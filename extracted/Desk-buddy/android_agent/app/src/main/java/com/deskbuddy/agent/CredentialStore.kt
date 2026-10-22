package com.deskbuddy.agent

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull

data class Credentials(val deviceId: String, val deviceToken: String, val gatewayUrl: String)

class CredentialStore(context: Context) {
    private val preferences = EncryptedSharedPreferences.create(
        context, "desk_buddy_agent", MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    fun save(deviceId: String, deviceToken: String, gatewayUrl: String) {
        require(deviceId.isNotBlank() && deviceToken.isNotBlank()) { "A device ID and token are required." }
        val url = gatewayUrl.toHttpUrlOrNull()
        require(url != null && url.scheme == "wss" && url.encodedPath.trimEnd('/') == "/ws/device" && url.query == null && url.fragment == null) {
            "Gateway URL must be wss://<host>/ws/device."
        }
        preferences.edit().putString("device_id", deviceId).putString("device_token", deviceToken).putString("gateway_url", gatewayUrl.trimEnd('/')).apply()
    }

    fun load(): Credentials? {
        val id = preferences.getString("device_id", null) ?: return null
        val token = preferences.getString("device_token", null) ?: return null
        val url = preferences.getString("gateway_url", null) ?: return null
        return Credentials(id, token, url)
    }
}
