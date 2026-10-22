/*
  Desk Buddy — ESP32-C3 Mini firmware (Phase 7)
  Protocol: gateway/docs/protocol.md

  Libraries (Arduino Library Manager):
    - arduinoWebSockets by Markus Sattler / Links2004
    - ArduinoJson by Benoit Blanchon

  Board package: Espressif ESP32 Arduino core >= 3.0.4.
  TLS: uses the ESP32 core's certificate bundle; certificate validation is NOT disabled.

  This firmware provides secure Render WebSocket authentication, heartbeat,
  reconnection, Serial Monitor text chat, and status/task-result handling.
  The current gateway protocol does NOT provide speech transcription or a
  device-originated Windows task-request message. See README.md before expecting
  microphone-based PC control.
*/

#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include <esp_arduino_version.h>
#include "config.h"

#if !defined(ESP32) || !defined(CONFIG_IDF_TARGET_ESP32C3)
  #warning "Select an ESP32-C3 board (for example ESP32C3 Dev Module / ESP32-C3 Super Mini)."
#endif

#if !defined(ESP_ARDUINO_VERSION) || ESP_ARDUINO_VERSION < ESP_ARDUINO_VERSION_VAL(3, 0, 4)
  #error "Desk Buddy requires ESP32 Arduino core 3.0.4+ for the built-in TLS CA bundle. Update the ESP32 board package."
#endif

static const char *GATEWAY_HOST = "desk-buddy-485q.onrender.com";
static const uint16_t GATEWAY_PORT = 443;
static const char *GATEWAY_PATH = "/ws/device";
static const uint32_t HEARTBEAT_FALLBACK_SECONDS = 25;
static const uint32_t WIFI_RETRY_INTERVAL_MS = 10000;
static const uint32_t CHAT_TIMEOUT_MS = 45000;

WebSocketsClient webSocket;
bool socketConnected = false;
bool authenticated = false;
uint32_t heartbeatSeconds = HEARTBEAT_FALLBACK_SECONDS;
uint32_t lastHeartbeatMs = 0;
uint32_t lastWifiAttemptMs = 0;
uint32_t reconnectDelayMs = 3000;
uint32_t lastChatSentMs = 0;
String pendingRequestId;
String serialLine;
uint32_t requestCounter = 0;
bool clockConfigured = false;

String makeRequestId() {
  ++requestCounter;
  String id = String((uint32_t)esp_random(), HEX);
  id += "-";
  id += String(millis(), HEX);
  id += "-";
  id += String(requestCounter);
  return id;
}

bool configLooksValid() {
  return strlen(WIFI_SSID) > 0 && strlen(WIFI_PASSWORD) > 0 &&
         strlen(DEVICE_ID) >= 3 && strlen(DEVICE_TOKEN) >= 8 &&
         String(WIFI_SSID) != "YOUR_WIFI_SSID" &&
         String(DEVICE_ID) != "YOUR_PAIRED_DEVICE_ID" &&
         String(DEVICE_TOKEN) != "YOUR_DEVICE_TOKEN_FROM_PAIRING";
}

void printHelp() {
  Serial.println();
  Serial.println(F("Desk Buddy ESP32-C3 commands:"));
  Serial.println(F("  Type a message and press Enter -> send chat to Render"));
  Serial.println(F("  /status  -> ask gateway for status acknowledgement"));
  Serial.println(F("  /help    -> show this help"));
  Serial.println();
}

void sendJson(JsonDocument &doc) {
  if (!socketConnected || !authenticated) {
    Serial.println(F("[offline] Not authenticated to Render yet."));
    return;
  }
  String output;
  serializeJson(doc, output);
  webSocket.sendTXT(output);
}

void sendHeartbeat() {
  StaticJsonDocument<96> doc;
  doc["type"] = "ping";
  sendJson(doc);
  lastHeartbeatMs = millis();
}

void sendChat(const String &message) {
  String trimmed = message;
  trimmed.trim();
  if (trimmed.isEmpty()) return;
  if (trimmed.length() > 4000) {
    Serial.println(F("Message too long. The gateway accepts up to 4000 characters."));
    return;
  }
  if (!socketConnected || !authenticated) {
    Serial.println(F("Not connected. Your message was not sent; please retry after reconnection."));
    return;
  }
  if (pendingRequestId.length()) {
    Serial.println(F("A chat request is still pending. Wait for Buddy's reply or its timeout before sending another."));
    return;
  }
  pendingRequestId = makeRequestId();
  lastChatSentMs = millis();
  StaticJsonDocument<4608> doc;
  doc["type"] = "chat";
  doc["request_id"] = pendingRequestId;
  doc["message"] = trimmed;
  sendJson(doc);
  Serial.println(String(F("[you] ")) + trimmed);
}

void sendStatus() {
  StaticJsonDocument<96> doc;
  doc["type"] = "status";
  sendJson(doc);
}

void sendTaskResult(const char *taskId, bool ok, const String &result) {
  StaticJsonDocument<512> doc;
  doc["type"] = "task_result";
  doc["task_id"] = taskId;
  doc["ok"] = ok;
  doc["result"] = result;
  sendJson(doc);
}

void handleGatewayMessage(uint8_t *payload, size_t length) {
  StaticJsonDocument<4096> doc;
  DeserializationError err = deserializeJson(doc, payload, length);
  if (err) {
    Serial.println(F("[gateway] Received malformed JSON."));
    return;
  }
  const char *type = doc["type"] | "";

  if (strcmp(type, "authenticated") == 0) {
    const char *returnedId = doc["device_id"] | "";
    if (String(returnedId) != String(DEVICE_ID)) {
      Serial.println(F("[security] Gateway returned a different device ID; disconnecting."));
      webSocket.disconnect();
      return;
    }
    heartbeatSeconds = doc["heartbeat_seconds"] | HEARTBEAT_FALLBACK_SECONDS;
    if (heartbeatSeconds < 5 || heartbeatSeconds > 120) heartbeatSeconds = HEARTBEAT_FALLBACK_SECONDS;
    authenticated = true;
    lastHeartbeatMs = millis();
    reconnectDelayMs = 3000;
    Serial.printf("[connected] Authenticated as %s; heartbeat every %lu seconds.\n", DEVICE_ID, (unsigned long)heartbeatSeconds);
    Serial.println(F("Type a message and press Enter to chat."));
    return;
  }

  if (strcmp(type, "pong") == 0) return;
  if (strcmp(type, "status_ack") == 0) {
    Serial.printf("[status] Wi-Fi=%s, RSSI=%d dBm, free heap=%u bytes\n",
                  WiFi.status() == WL_CONNECTED ? "connected" : "disconnected",
                  WiFi.RSSI(), ESP.getFreeHeap());
    return;
  }
  if (strcmp(type, "chat_response") == 0) {
    const char *requestId = doc["request_id"] | "";
    const char *answer = doc["answer"] | "";
    if (pendingRequestId.length() && pendingRequestId != String(requestId)) {
      Serial.println(F("[gateway] Response belongs to a different request; ignoring it."));
      return;
    }
    pendingRequestId = "";
    Serial.println();
    Serial.print(F("[Buddy] "));
    Serial.println(answer);
    Serial.println();
    return;
  }
  if (strcmp(type, "chat_error") == 0) {
    const char *code = doc["code"] | "unknown_error";
    const char *message = doc["message"] | "Chat request failed.";
    pendingRequestId = "";
    Serial.printf("[chat error: %s] %s\n", code, message);
    return;
  }
  if (strcmp(type, "task") == 0) {
    // Only acknowledge the safe, local get_status action. This device does not
    // execute arbitrary commands and does not control the Windows agent.
    const char *taskId = doc["task_id"] | "";
    const char *actionName = doc["action"]["name"] | "";
    if (strlen(taskId) == 0) return;
    if (strcmp(actionName, "get_status") == 0) {
      String result = "ESP32-C3 online; Wi-Fi connected; RSSI=" + String(WiFi.RSSI()) + " dBm; free_heap=" + String(ESP.getFreeHeap());
      sendTaskResult(taskId, true, result);
    } else {
      sendTaskResult(taskId, false, "This ESP32-C3 firmware does not support that action.");
    }
    return;
  }
  if (strcmp(type, "task_result_ack") == 0) return;
  if (strcmp(type, "error") == 0) {
    Serial.printf("[gateway error] %s\n", doc["message"] | "Unknown error");
    return;
  }
  Serial.printf("[gateway] Unhandled message type: %s\n", type);
}

void webSocketEvent(WStype_t eventType, uint8_t *payload, size_t length) {
  switch (eventType) {
    case WStype_DISCONNECTED:
      if (socketConnected || authenticated) Serial.println(F("[network] WebSocket disconnected; reconnecting automatically."));
      socketConnected = false;
      authenticated = false;
      pendingRequestId = "";
      reconnectDelayMs = min((uint32_t)60000, max((uint32_t)3000, reconnectDelayMs * 2));
      webSocket.setReconnectInterval(reconnectDelayMs);
      break;
    case WStype_CONNECTED: {
      socketConnected = true;
      authenticated = false;
      Serial.printf("[network] WSS connected to %s; authenticating device...\n", GATEWAY_HOST);
      StaticJsonDocument<512> auth;
      auth["type"] = "auth";
      auth["device_id"] = DEVICE_ID;
      auth["token"] = DEVICE_TOKEN;
      String output;
      serializeJson(auth, output);
      webSocket.sendTXT(output);
      break;
    }
    case WStype_TEXT:
      handleGatewayMessage(payload, length);
      break;
    case WStype_ERROR:
      Serial.println(F("[network] WebSocket/TLS error. Check Wi-Fi, Render URL, certificate bundle and device time."));
      break;
    default:
      break;
  }
}

void startSecureWebSocket() {
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(reconnectDelayMs);
  // Built-in ESP32 certificate bundle validates Render's TLS certificate.
  // Do not replace this with setInsecure().
  webSocket.beginSslWithBundle(GATEWAY_HOST, GATEWAY_PORT, GATEWAY_PATH, nullptr, 0);
}

void ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!clockConfigured) {
      configTime(0, 0, "pool.ntp.org", "time.google.com", "time.cloudflare.com");
      clockConfigured = true;
      Serial.println(F("[time] NTP synchronization started for TLS certificate validation."));
    }
    return;
  }
  if (millis() - lastWifiAttemptMs < WIFI_RETRY_INTERVAL_MS) return;
  lastWifiAttemptMs = millis();
  Serial.printf("[wifi] Connecting to SSID '%s'...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

void processSerial() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      String line = serialLine;
      serialLine = "";
      line.trim();
      if (line.isEmpty()) continue;
      if (line == "/help") printHelp();
      else if (line == "/status") sendStatus();
      else if (line.startsWith("/")) Serial.println(F("Unknown command. Type /help."));
      else sendChat(line);
    } else if (serialLine.length() < 4000) {
      serialLine += c;
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println();
  Serial.println(F("Desk Buddy ESP32-C3 — Phase 7"));
  if (!configLooksValid()) {
    Serial.println(F("CONFIG ERROR: Copy config.example.h to config.h and enter Wi-Fi plus paired device credentials."));
    while (true) delay(1000);
  }
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print(F("Connecting to Wi-Fi"));
  uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 20000) {
    delay(300);
    Serial.print('.');
  }
  Serial.println();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(F("Wi-Fi not connected yet; the firmware will keep retrying."));
  } else {
    Serial.printf("[wifi] Connected; IP=%s; RSSI=%d dBm\n", WiFi.localIP().toString().c_str(), WiFi.RSSI());
    // ensureWifi() starts NTP synchronization. The WebSocket library retries
    // until the system clock is valid and the server certificate can be checked.
    ensureWifi();
  }
  startSecureWebSocket();
  printHelp();
}

void loop() {
  ensureWifi();
  webSocket.loop();
  processSerial();

  if (authenticated && millis() - lastHeartbeatMs >= heartbeatSeconds * 1000UL) {
    sendHeartbeat();
  }
  if (pendingRequestId.length() && millis() - lastChatSentMs > CHAT_TIMEOUT_MS) {
    Serial.println(F("[chat] No reply received within 45 seconds. The gateway/model may be unavailable."));
    pendingRequestId = "";
  }
  delay(2);
}
