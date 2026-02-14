🍱 Apna Dabba
Subscription-Based Meal Management Platform

Apna Dabba is a Django-based web application designed to digitize and automate local tiffin subscription services. It connects customers with tiffin providers through a structured subscription model, daily meal tracking, and automated lifecycle management.

🚀 Features
👤 Customer Features

User registration & secure authentication

Browse available menus

Select subscription plans

Subscription lifecycle tracking

Active subscription dashboard

Daily meal status visualization

👨‍🍳 Owner Features

Role-based dashboard

Menu creation & management

Subscription plan management

Daily meal tracking (Taken / Skipped)

Automated extension logic

Revenue analytics & subscriber monitoring

⚙ System Features

Role-based access control (Owner / Customer)

Automated subscription start & expiry

Skip-based extension system

Secure authentication (Django Auth)

CSRF protection

Clean modular architecture

🏗 System Architecture
User Interface (HTML, CSS, JS)
        ↓
Django Views (Business Logic)
        ↓
Django ORM (Models)
        ↓
Database (SQLite / PostgreSQL)


The system follows a layered architecture ensuring maintainability, scalability, and security.

🛠 Tech Stack

Backend

Django

Django ORM

SQLite (Development)

PostgreSQL (Production-ready)

Frontend

HTML5

CSS3

JavaScript

Security

Django Authentication System

Role-based access control

CSRF Protection

📊 Core Business Logic
Subscription Creation

On payment success:

start_date = today

end_date = today + duration

is_active = True

Skip Extension

If a meal is marked as "Skipped":

end_date += 1 day

Auto Expiry

If current date exceeds end_date:

Subscription automatically becomes inactive

📦 Installation Guide
1️⃣ Clone the Repository
git clone https://github.com/your-username/apna-dabba.git
cd apna-dabba

2️⃣ Create Virtual Environment
python -m venv venv

3️⃣ Activate Virtual Environment

Windows:

venv\Scripts\activate


Mac/Linux:

source venv/bin/activate

4️⃣ Install Dependencies
pip install -r requirements.txt

5️⃣ Run Migrations
python manage.py makemigrations
python manage.py migrate

6️⃣ Create Superuser
python manage.py createsuperuser

7️⃣ Run Development Server
python manage.py runserver


Open:

http://127.0.0.1:8000/

🔐 Default Roles

Customer → is_staff = False

Owner → is_staff = True

📈 Future Scope

Payment gateway integration

Mobile application development

Advanced analytics dashboard

Multi-city expansion

AI-based subscription recommendations

📁 Project Structure
apna_dabba/
│
├── core/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── templates/
│   ├── static/
│
├── apna_dabba/
│   ├── settings.py
│   ├── urls.py
│
├── manage.py

🎯 Objective

To build a scalable, automated subscription-based platform that modernizes local tiffin services through structured business logic and secure backend architecture.
