# Verwende ein Python-Basisimage
FROM python:3.11-slim

# Setze Arbeitsverzeichnis
WORKDIR /app

# Kopiere die erforderlichen Dateien ins Image
COPY ip_monitor.py .
COPY config.json .
COPY requirements.txt .

# Installiere die benötigten Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Exponiere keinen Port, da dies kein Web-Service ist
# (optional)
# EXPOSE 8000

# Definiere Umgebungsvariablen-Datei
COPY .env /app/.env

# Führe das Skript aus
CMD ["python", "ip_monitor.py"]
