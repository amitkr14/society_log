# 🏢 Society Log - Digital Visitor Management

A secure, multi-role Django application designed to replace traditional paper-based society visitor logs with a modern, OTP-verified system.

## 🌟 Major Updates (May 2026)
Successfully transitioned the project from a single-user prototype to a production-ready multi-role ecosystem.

### Key Technical Milestones:
*   **Intelligent Routing:** Implemented a `login_redirect` traffic-cop view to automatically funnel Residents and Guards to their respective dashboards upon login[cite: 2].
*   **Secure OTP Lifecycle:** Developed a "burn-on-use" OTP system where residents generate 6-digit codes and guards verify them to trigger automated entry logs[cite: 1, 2].
*   **Timezone Synchronization:** Refactored backend logic to use `Asia/Kolkata` (IST) with `timezone.localdate()`, ensuring midnight rollovers and daily analytics are 100% accurate to the local clock.
*   **Dynamic UI:** Added JavaScript-driven form elements to handle "Other" purpose specifications without page reloads.

## 🛠️ Tech Stack
*   **Core:** Python 3.12, Django 6.0.4[cite: 2]
*   **Database:** PostgreSQL
*   **Infrastructure:** Docker & Docker-Compose
*   **Auth:** Django Built-in Auth with custom profile linking (1-to-1 relationships)[cite: 1, 2]

## 🚀 How to Run
1. `docker-compose up --build`
2. `docker-compose exec web python manage.py migrate`
3. Access the **Landing Page** at `http://localhost:8000/`[cite: 2]