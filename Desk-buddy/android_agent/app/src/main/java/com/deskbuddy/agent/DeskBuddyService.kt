package com.deskbuddy.agent

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.net.Uri
import android.os.IBinder
import androidx.core.app.NotificationCompat
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledFuture
import java.util.concurrent.TimeUnit

class DeskBuddyService : Service() {
    private val client = OkHttpClient.Builder().pingInterval(20, TimeUnit.SECONDS).build()
    private var socket: WebSocket? = null
    private var reconnectDelaySeconds = 1L
    private var reconnecting = false
    private var authenticated = false
    private val scheduler = Executors.newSingleThreadScheduledExecutor()
    private var heartbeatTask: ScheduledFuture<*>? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(NOTIFICATION_ID, notification("Connecting"))
        connect()
        return START_STICKY
    }

    override fun onDestroy() {
        socket?.close(1000, "Service stopped")
        heartbeatTask?.cancel(false)
        scheduler.shutdownNow()
        client.dispatcher.executorService.shutdown()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun connect() {
        val credentials = CredentialStore(this).load() ?: run {
            stopSelf()
            return
        }
        socket = client.newWebSocket(Request.Builder().url(credentials.gatewayUrl).build(), object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                webSocket.send(JSONObject().put("type", "auth").put("device_id", credentials.deviceId).put("token", credentials.deviceToken).toString())
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                handleMessage(webSocket, text)
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                webSocket.close(code, reason)
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) = scheduleReconnect()
            override fun onFailure(webSocket: WebSocket, error: Throwable, response: Response?) = scheduleReconnect()
        })
    }

    private fun handleMessage(webSocket: WebSocket, text: String) {
        val message = try { JSONObject(text) } catch (_: Exception) { return }
        when (message.optString("type")) {
            "authenticated" -> {
                authenticated = true
                reconnectDelaySeconds = 1
                startHeartbeat(webSocket, message.optInt("heartbeat_seconds"))
                updateNotification("Connected")
            }
            "task" -> if (authenticated) handleTask(webSocket, message)
        }
    }

    private fun handleTask(webSocket: WebSocket, message: JSONObject) {
        val taskId = message.optString("task_id")
        if (taskId.isBlank()) return
        val action = message.optJSONObject("action")
        val result = JSONObject().put("type", "task_result").put("task_id", taskId)
        try {
            when (action?.optString("name")) {
                "get_status" -> result.put("ok", true).put("result", "Android agent is connected and ready.")
                "open_url" -> {
                    val url = action.optJSONObject("args")?.optString("url") ?: throw IllegalArgumentException("Missing URL.")
                    val uri = Uri.parse(url)
                    require(uri.scheme == "http" || uri.scheme == "https") { "Only HTTP(S) URLs are allowed." }
                    require(!uri.host.isNullOrBlank() && uri.userInfo == null) { "The URL is invalid." }
                    startActivity(Intent(Intent.ACTION_VIEW, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                    result.put("ok", true).put("result", "Opened the requested URL.")
                }
                else -> throw IllegalArgumentException("This Android agent action is not allowed.")
            }
        } catch (error: Exception) {
            result.put("ok", false).put("result", error.message ?: "The action could not be completed.")
        }
        webSocket.send(result.toString())
    }

    private fun scheduleReconnect() {
        if (reconnecting) return
        authenticated = false
        heartbeatTask?.cancel(false)
        reconnecting = true
        val delay = reconnectDelaySeconds
        reconnectDelaySeconds = (reconnectDelaySeconds * 2).coerceAtMost(60)
        Thread {
            Thread.sleep(delay * 1000)
            reconnecting = false
            connect()
        }.start()
    }

    private fun startHeartbeat(webSocket: WebSocket, seconds: Int) {
        if (seconds <= 0) {
            webSocket.close(1002, "Invalid heartbeat interval")
            return
        }
        heartbeatTask?.cancel(false)
        heartbeatTask = scheduler.scheduleAtFixedRate(
            { webSocket.send(JSONObject().put("type", "ping").toString()) },
            seconds.toLong(), seconds.toLong(), TimeUnit.SECONDS
        )
    }

    private fun notification(text: String) = NotificationCompat.Builder(this, CHANNEL_ID)
        .setSmallIcon(android.R.drawable.stat_notify_sync)
        .setContentTitle("Desk Buddy Agent")
        .setContentText(text)
        .setContentIntent(PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE))
        .setOngoing(true)
        .build()

    private fun updateNotification(text: String) {
        (getSystemService(NotificationManager::class.java)).notify(NOTIFICATION_ID, notification(text))
    }

    override fun onCreate() {
        super.onCreate()
        getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel(CHANNEL_ID, "Desk Buddy agent", NotificationManager.IMPORTANCE_LOW))
    }

    companion object {
        private const val CHANNEL_ID = "desk_buddy_agent"
        private const val NOTIFICATION_ID = 1
    }
}
