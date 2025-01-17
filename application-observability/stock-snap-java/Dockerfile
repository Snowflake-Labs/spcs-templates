# Use an official OpenJDK runtime as a parent image
FROM openjdk:17-jdk-slim

# Set the working directory in the container
WORKDIR /app

# Copy the fat jar file to the container
COPY target/stock-snap-java-1.0-SNAPSHOT-jar-with-dependencies.jar /app/stock-snap-java.jar

# Expose the port the application runs on
EXPOSE 8080

# Run the application
CMD ["java", "-Dorg.slf4j.simpleLogger.logFile=System.out", "-jar", "stock-snap-java.jar"]
