FROM eclipse-temurin:17-jdk-jammy AS build
WORKDIR /app

# Install Gradle 8.5 (compatible with shadow plugin 8.1.1)
RUN apt-get update && apt-get install -y wget unzip && \
    wget -q https://services.gradle.org/distributions/gradle-8.5-bin.zip && \
    unzip -q gradle-8.5-bin.zip && \
    mv gradle-8.5 /opt/gradle && \
    rm gradle-8.5-bin.zip && \
    ln -s /opt/gradle/bin/gradle /usr/bin/gradle

COPY build.gradle settings.gradle ./
COPY src ./src

RUN gradle shadowJar --no-daemon

FROM eclipse-temurin:17-jre-jammy
WORKDIR /app
COPY --from=build /app/build/libs/*-all.jar app.jar
CMD ["java", "-jar", "app.jar"]
