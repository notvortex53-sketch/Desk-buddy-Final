# Desk Buddy Windows Agent

This outbound agent connects to the paired Gateway over WSS. Its paired device
token is stored in Windows Credential Manager; the local configuration file
contains only the device ID and gateway URL.

Install its dependencies, then register using a Windows device ID and token
returned by the existing pairing flow:

```powershell
py -m pip install -r requirements.txt
py desk_buddy_agent.py register --device-id <paired-device-id> --device-token <shown-once-device-token> --gateway-url wss://<render-host>/ws/device
py desk_buddy_agent.py run
```

The agent reconnects with exponential backoff after network, Render, or the
hourly `4003` reauthentication disconnect. It deliberately permits only
`get_status` and an `open_url` task containing one credential-free HTTP(S)
URL. It never runs shell commands, scripts, or arbitrary programs. Every
Windows task must carry the gateway's Ethical Mode owner authorization; the
agent rejects unapproved tasks even if they reach its WebSocket.
