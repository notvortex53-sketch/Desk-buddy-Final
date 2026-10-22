# Desk Buddy Android Agent

This Android app is an outbound WSS connector for a paired `android` device.
It stores the device ID, device token, and gateway address in encrypted Android
app storage and runs as a visible foreground service while connected.

## Permissions and supported actions

- `INTERNET` is required for the WSS connection.
- Android 13+ requests notification permission so connection state can remain
  visible; the foreground-service notification is always created.
- The app accepts only `get_status` and `open_url`. `open_url` accepts only an
  HTTP(S) URI without user-info and launches Android's normal URL handler.
- No contacts, microphone, location, accessibility, storage, shell, or app
  automation permissions are requested.

Enter the paired Android device ID, its shown-once token, and the public
`wss://<render-host>/ws/device` URL in the app. The gateway requires a fresh
authentication every hour and the app reconnects with exponential backoff after
network, Render, or `4003` reauthentication disconnects.
