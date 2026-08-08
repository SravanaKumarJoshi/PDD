package com.biopolymer.screening.ui.settings

import android.content.Intent
import android.widget.Toast
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.google.firebase.auth.FirebaseUser

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    viewModel: SettingsViewModel = hiltViewModel(),
) {
    val context = LocalContext.current
    val userPreferences by viewModel.userPreferences.collectAsState()
    val currentUser     by viewModel.currentUser.collectAsState()
    var showDeleteDialog by remember { mutableStateOf(false) }

    if (showDeleteDialog) {
        AlertDialog(
            onDismissRequest = { showDeleteDialog = false },
            title = { Text("Delete All Data") },
            text  = { Text("Are you sure you want to delete all local saved projects? This cannot be undone.") },
            confirmButton = {
                TextButton(onClick = {
                    viewModel.deleteAllData {
                        Toast.makeText(context, "Saved projects deleted", Toast.LENGTH_SHORT).show()
                    }
                    showDeleteDialog = false
                }) { Text("Delete", color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteDialog = false }) { Text("Cancel") }
            },
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title  = { Text("Settings") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor    = MaterialTheme.colorScheme.surface,
                    titleContentColor = MaterialTheme.colorScheme.onSurface,
                ),
            )
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState()),
        ) {
            ProfileSection(user = currentUser, onSignInClick = {
                context.startActivity(Intent(context, com.biopolymer.screening.LoginActivity::class.java))
            })

            // ── Server Configuration Section ───────────────────────────
            ServerConfigurationSection(viewModel = viewModel)

            if (currentUser != null) {
                SettingsSection("Account") {
                    SettingsItem(
                        icon     = Icons.AutoMirrored.Filled.Logout,
                        title    = "Logout",
                        subtitle = "Sign out of your account",
                        onClick  = {
                            viewModel.logout {
                                val intent = Intent(context, com.biopolymer.screening.LoginActivity::class.java).apply {
                                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                                }
                                context.startActivity(intent)
                            }
                        },
                        titleColor = MaterialTheme.colorScheme.error,
                    )
                }
            }

            // ── Data section ───────────────────────────────────────────
            SettingsSection("Data & Export") {
                SettingsItem(
                    icon     = Icons.Filled.Download,
                    title    = "Export My Data",
                    subtitle = "Share all projects as text",
                    onClick  = {
                        viewModel.exportData { jsonString ->
                            context.startActivity(Intent.createChooser(Intent().apply {
                                action = Intent.ACTION_SEND
                                putExtra(Intent.EXTRA_TEXT, jsonString)
                                type = "text/plain"
                            }, "Export Data"))
                        }
                    },
                )

                SettingsItem(
                    icon       = Icons.Filled.DeleteForever,
                    title      = "Delete Saved Projects",
                    subtitle   = "Remove all saved projects",
                    onClick    = { showDeleteDialog = true },
                    titleColor = MaterialTheme.colorScheme.error,
                )
            }

            // ── Privacy section ───────────────────────────────────────────────
            SettingsSection("Privacy & Analytics") {
                SettingsItem(
                    icon     = Icons.Filled.PrivacyTip,
                    title    = "Privacy Policy",
                    subtitle = "Read our data handling practices",
                    onClick  = {
                        context.startActivity(
                            Intent(Intent.ACTION_VIEW,
                                android.net.Uri.parse("https://yourapp.com/privacy"))
                        )
                    },
                )
            }

            // ── Appearance section ────────────────────────────────────────────
            SettingsSection("Appearance") {
                SettingsToggle(
                    icon           = Icons.Filled.DarkMode,
                    title          = "Dark Mode",
                    subtitle       = "Override system default",
                    checked        = userPreferences.darkMode,
                    onCheckedChange = { viewModel.setDarkMode(it) },
                )
            }

            // ── About section ─────────────────────────────────────────────────
            SettingsSection("About") {
                SettingsItem(
                    icon     = Icons.Filled.Info,
                    title    = "Version",
                    subtitle = "2.0.0 (Server-Side AI Screening Edition)",
                    onClick  = {},
                )
            }

            Spacer(modifier = Modifier.height(32.dp))
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Reusable settings UI primitives
// ─────────────────────────────────────────────────────────────────────────────

@Composable
fun ProfileSection(user: FirebaseUser?, onSignInClick: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(16.dp),
        colors   = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Row(
            modifier          = Modifier.padding(16.dp).fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Surface(
                modifier = Modifier.size(64.dp).clip(CircleShape),
                color    = MaterialTheme.colorScheme.primaryContainer,
            ) {
                Icon(
                    imageVector        = Icons.Filled.Person,
                    contentDescription = null,
                    modifier           = Modifier.padding(12.dp),
                    tint               = MaterialTheme.colorScheme.onPrimaryContainer,
                )
            }
            Spacer(Modifier.width(16.dp))
            Column(modifier = Modifier.weight(1f)) {
                if (user != null) {
                    Text(
                        text       = user.displayName ?: "No Display Name",
                        style      = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text  = user.email ?: "",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        text     = "Authenticated",
                        style    = MaterialTheme.typography.labelSmall,
                        color    = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(top = 4.dp),
                    )
                } else {
                    Text(
                        text       = "Guest Mode",
                        style      = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                    )
                    Text(
                        text  = "Sign in to enable cloud features",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
            if (user == null) {
                Button(onClick = onSignInClick) { Text("Sign In") }
            }
        }
    }
}

@Composable
fun SettingsSection(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(modifier = Modifier.padding(top = 8.dp)) {
        Text(
            text     = title,
            style    = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.Bold,
            color    = MaterialTheme.colorScheme.primary,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
        )
        content()
        HorizontalDivider(
            modifier  = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
            thickness = 0.5.dp,
            color     = MaterialTheme.colorScheme.outlineVariant,
        )
    }
}

@Composable
fun SettingsItem(
    icon: ImageVector,
    title: String,
    subtitle: String,
    onClick: () -> Unit,
    titleColor: androidx.compose.ui.graphics.Color = MaterialTheme.colorScheme.onSurface,
    trailing: @Composable (() -> Unit)? = null,
) {
    ListItem(
        modifier         = Modifier.clickable { onClick() },
        headlineContent  = { Text(title, color = titleColor) },
        supportingContent = { Text(subtitle, style = MaterialTheme.typography.bodySmall) },
        leadingContent   = {
            Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
        },
        trailingContent  = trailing,
    )
}

@Composable
fun SettingsToggle(
    icon: ImageVector,
    title: String,
    subtitle: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
) {
    ListItem(
        headlineContent  = { Text(title) },
        supportingContent = { Text(subtitle, style = MaterialTheme.typography.bodySmall) },
        leadingContent   = {
            Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant)
        },
        trailingContent  = {
            Switch(
                checked       = checked,
                onCheckedChange = onCheckedChange,
                thumbContent  = if (checked) {
                    {
                        Icon(
                            imageVector        = Icons.Filled.Check,
                            contentDescription = null,
                            modifier           = Modifier.size(SwitchDefaults.IconSize),
                        )
                    }
                } else null,
            )
        },
    )
}

@Composable
fun ServerConfigurationSection(viewModel: SettingsViewModel) {
    val activeBaseUrl by viewModel.currentBaseUrl.collectAsState()
    val userPrefs by viewModel.userPreferences.collectAsState()
    val testResult by viewModel.connectionTestResult.collectAsState()
    val discoveryResult by viewModel.discoveryResult.collectAsState()

    var inputUrl by remember(activeBaseUrl) { mutableStateOf(userPrefs.customBaseUrl ?: activeBaseUrl) }

    LaunchedEffect(discoveryResult.discoveredUrl) {
        discoveryResult.discoveredUrl?.let {
            inputUrl = it
        }
    }

    SettingsSection("Server Configuration") {
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = "Active Server URL",
                        style = MaterialTheme.typography.titleSmall,
                        fontWeight = FontWeight.Bold,
                    )
                    Surface(
                        color = if (userPrefs.customBaseUrl != null) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.secondaryContainer,
                        shape = CircleShape,
                    ) {
                        Text(
                            text = if (userPrefs.customBaseUrl != null) "Custom Override" else "Auto-Detected",
                            style = MaterialTheme.typography.labelSmall,
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                            color = if (userPrefs.customBaseUrl != null) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onSecondaryContainer,
                        )
                    }
                }

                Text(
                    text = activeBaseUrl,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 4.dp, bottom = 12.dp)
                )

                OutlinedTextField(
                    value = inputUrl,
                    onValueChange = { inputUrl = it },
                    label = { Text("FastAPI Server URL") },
                    placeholder = { Text("http://192.168.1.50:8000/") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                    trailingIcon = {
                        if (inputUrl.isNotEmpty()) {
                            IconButton(onClick = { inputUrl = "" }) {
                                Icon(Icons.Filled.Clear, contentDescription = "Clear")
                            }
                        }
                    }
                )

                Spacer(modifier = Modifier.height(12.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Button(
                        onClick = { viewModel.testConnection(inputUrl) },
                        enabled = !testResult.isTesting,
                        modifier = Modifier.weight(1f)
                    ) {
                        if (testResult.isTesting) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                        } else {
                            Icon(Icons.Filled.NetworkCheck, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(Modifier.width(4.dp))
                            Text("Test")
                        }
                    }

                    OutlinedButton(
                        onClick = { viewModel.saveServerUrl(inputUrl) },
                        enabled = inputUrl.isNotBlank() && !testResult.isTesting,
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Filled.Save, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.width(4.dp))
                        Text("Save")
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedButton(
                        onClick = { viewModel.discoverServer() },
                        enabled = !discoveryResult.isScanning,
                        modifier = Modifier.weight(1f)
                    ) {
                        if (discoveryResult.isScanning) {
                            CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                        } else {
                            Icon(Icons.Filled.Search, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(Modifier.width(4.dp))
                            Text("Auto Discover")
                        }
                    }

                    if (userPrefs.customBaseUrl != null) {
                        TextButton(
                            onClick = {
                                viewModel.resetServerUrl()
                            },
                            modifier = Modifier.weight(0.8f)
                        ) {
                            Text("Reset")
                        }
                    }
                }

                // Subnet discovery result message
                discoveryResult.statusMessage?.let { status ->
                    Text(
                        text = status,
                        style = MaterialTheme.typography.bodySmall,
                        color = if (discoveryResult.discoveredUrl != null) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 8.dp)
                    )
                }

                // Connection Test Feedback
                testResult.message?.let { msg ->
                    Spacer(modifier = Modifier.height(12.dp))
                    val isSuccess = testResult.isSuccess == true
                    Card(
                        colors = CardDefaults.cardColors(
                            containerColor = if (isSuccess) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.errorContainer
                        ),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    imageVector = if (isSuccess) Icons.Filled.CheckCircle else Icons.Filled.Warning,
                                    contentDescription = null,
                                    tint = if (isSuccess) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onErrorContainer
                                )
                                Spacer(Modifier.width(8.dp))
                                Text(
                                    text = if (isSuccess) "Connection Successful" else "Connection Failed",
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold,
                                    color = if (isSuccess) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onErrorContainer
                                )
                                testResult.latencyMs?.let { latency ->
                                    Spacer(Modifier.weight(1f))
                                    Text(
                                        text = "${latency}ms",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = if (isSuccess) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onErrorContainer
                                    )
                                }
                            }
                            Spacer(Modifier.height(4.dp))
                            Text(
                                text = msg,
                                style = MaterialTheme.typography.bodySmall,
                                color = if (isSuccess) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onErrorContainer
                            )
                        }
                    }
                }
            }
        }
    }
}
