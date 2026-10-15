plugins { alias(libs.plugins.android); alias(libs.plugins.kotlin); alias(libs.plugins.compose); alias(libs.plugins.serialization) }
android {
 namespace = "org.vowen.app"
 compileSdk = 36
 buildToolsVersion = "36.0.0"
 defaultConfig { applicationId = "org.vowen.app"; minSdk = 26; targetSdk = 36; versionCode = 1; versionName = "0.1.0-alpha" }
 compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
 kotlinOptions { jvmTarget = "17" }
 buildFeatures { compose = true }
}
dependencies {
 implementation(libs.compose.ui); implementation(libs.compose.material); implementation(libs.activity.compose)
 implementation(libs.coroutines.android); implementation(libs.serialization.json); implementation(libs.okhttp)
 testImplementation(libs.junit)
}
dependencyLocking { lockAllConfigurations() }
