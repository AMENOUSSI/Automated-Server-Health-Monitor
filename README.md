# Automated Server Health Monitor 🚀

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Linux](https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black)
![Postfix](https://img.shields.io/badge/Postfix-FFA500?style=for-the-badge&logo=mail-dot-ru&logoColor=white)

A comprehensive system monitoring solution that combines a self-hosted network infrastructure with Python-driven automation to ensure high availability and proactive server management.

## 📌 Overview

This project was developed to automate the critical task of monitoring server resources. Unlike standard scripts, this solution relies on a **fully self-administered infrastructure**, including a custom DNS server and a Postfix MTA, demonstrating a deep understanding of the entire data pipeline and system administration.

## 🛠 Tech Stack

* **Language:** Python 3.13.5
* **Infrastructure:** * **Postfix:** Configured as a local Mail Transfer Agent (MTA) for secure report dispatching.
    * **DNS Server:** Self-hosted for internal hostname resolution and network reliability.
* **OS Environment:** Linux Virtual Machine (VM).
* **Key Libraries:** `smtplib`, `email.mime`, `psutil` (or native subprocess calls).

## ✨ Key Features

* **Real-time Storage Analysis:** Automatically monitors critical partitions such as `/home` and `/boot`.
* **Automated HTML Reporting:** Generates clean, professional status tables including:
    * Total Capacity
    * Used Space
    * Available Space
    * Usage Percentage (%)
* **Autonomous Alerting:** Scheduled dispatch of server health reports via the internal SMTP relay.
* **Observability:** Provides immediate visibility into system health to prevent data pipeline failures.

## 📊 Sample Output

The system generates structured email reports as shown below:

![Automated-Server-Health-Monitor](./server_monitor.png)

## 🚀 Why This Matters

As an aspiring **Data Engineer**, I believe that observability is the backbone of any robust data architecture. By building the infrastructure (DNS/SMTP) from scratch before implementing the automation logic, I ensured a highly autonomous and secure monitoring environment. This project showcases my ability to bridge the gap between **Software Development** and **System Operations (DevOps)**.

## 📝 License

This project is open-source and available under the [MIT License](LICENSE).
