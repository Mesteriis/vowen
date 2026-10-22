plugins { alias(libs.plugins.android); alias(libs.plugins.kotlin); alias(libs.plugins.compose); alias(libs.plugins.serialization) }
android {
 namespace = "org.vowen.app"
 compileSdk = 36
 buildToolsVersion = "36.0.0"
 defaultConfig { applicationId = "org.vowen.app"; minSdk = 26; targetSdk = 36; versionCode = providers.gradleProperty("vowenVersionCode").orNull?.toInt() ?: 1; versionName = providers.gradleProperty("vowenVersionName").orNull ?: "0.1.0-alpha"; testInstrumentationRunner = "org.vowen.app.VowenTestRunner" }
 compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
 kotlinOptions { jvmTarget = "17" }
 sourceSets.getByName("main").res.srcDir(rootProject.file("../static/android/res"))
 buildFeatures { compose = true }
}
dependencies {
 implementation(libs.commonmark)
 implementation(libs.compose.ui); implementation(libs.compose.material); implementation(libs.activity.compose)
 implementation(libs.coroutines.android); implementation(libs.serialization.json); implementation(libs.okhttp)
 testImplementation(libs.junit)
 androidTestImplementation("androidx.compose.ui:ui-test-junit4:1.9.3")
 androidTestImplementation("androidx.test:runner:1.6.2")
 debugImplementation("androidx.compose.ui:ui-test-manifest:1.9.3")
}
dependencyLocking { lockAllConfigurations() }
