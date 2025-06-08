allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.buildDir = file("build")
subprojects {
    project.buildDir = file("${rootProject.buildDir}/${project.name}")
}

tasks.register<Delete>("clean") {
    delete(rootProject.buildDir)
}
