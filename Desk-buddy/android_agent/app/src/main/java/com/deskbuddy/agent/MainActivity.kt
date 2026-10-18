package com.deskbuddy.agent

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {
    private val notificationPermission = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val credentials = CredentialStore(this).load()
        val deviceId = EditText(this).apply { hint = "Paired device ID"; setText(credentials?.deviceId) }
        val token = EditText(this).apply { hint = "Device token"; setText(credentials?.deviceToken) }
        val gateway = EditText(this).apply { hint = "wss://host/ws/device"; setText(credentials?.gatewayUrl) }
        val connect = Button(this).apply { text = "Save and connect" }
        connect.setOnClickListener {
            try {
                CredentialStore(this).save(deviceId.text.toString(), token.text.toString(), gateway.text.toString())
                requestNotificationPermission()
                ContextCompat.startForegroundService(this, Intent(this, DeskBuddyService::class.java))
                Toast.makeText(this, "Desk Buddy agent connecting", Toast.LENGTH_SHORT).show()
            } catch (error: IllegalArgumentException) {
                Toast.makeText(this, error.message, Toast.LENGTH_LONG).show()
            }
        }
        setContentView(LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val padding = (24 * resources.displayMetrics.density).toInt()
            setPadding(padding, padding, padding, padding)
            addView(deviceId); addView(token); addView(gateway); addView(connect)
        })
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
}
