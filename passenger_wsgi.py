# -*- coding: utf-8 -*-
"""
Entry point untuk cPanel (Phusion Passenger / WSGI).

Saat membuat aplikasi lewat cPanel > Setup Python App:
  - Application startup file : passenger_wsgi.py
  - Application Entry point   : application
Passenger akan otomatis mencari objek bernama `application` di file ini.
"""
from app import app as application

if __name__ == "__main__":
    application.run()
