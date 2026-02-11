@echo off
set RABBITMQ_URL=amqp://admin:admin123@localhost:5672/
set PORT=8080
go run main.go
pause
