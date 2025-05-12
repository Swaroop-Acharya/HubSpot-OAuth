
# 🧩 VectorShift Integrations Technical Assessment

This repository contains a full-stack project built as part of the VectorShift interview process. It demonstrates the integration of third-party services (specifically HubSpot) using OAuth2 with a **React frontend** and a **FastAPI backend**.

---

## 📌 Project Overview

This assessment includes the implementation of a new integration (HubSpot) in an existing integrations system. Two parts are covered:

### ✅ Part 1: HubSpot OAuth Integration
- Implemented OAuth2 flow for HubSpot (`authorize_hubspot`, `oauth2callback_hubspot`, and `get_hubspot_credentials`).
- Followed existing integration structures (Airtable, Notion) for consistency.
- Built `hubspot.js` in the frontend to support the OAuth flow and integrate HubSpot into the UI.
- Registered a test app with HubSpot to generate client ID and secret for testing purposes.

### ✅ Part 2: Load HubSpot Items
- Implemented `get_items_hubspot` to fetch and transform data from HubSpot APIs into `IntegrationItem` objects.
- Used relevant endpoints (e.g., Contacts, Deals) to gather meaningful integration data.
- Displayed results via console logging (as suggested).

---

## 🛠️ Tech Stack

### Backend
- 🐍 Python 3
- ⚡ FastAPI
- 🧠 Redis
- 🔐 OAuth2

### Frontend
- ⚛️ React
- 📦 JavaScript (ES6)
- 💅 TailwindCSS (if present)

---

## 🚀 Getting Started

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
redis-server  # Ensure Redis is running
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

---

## 🔑 OAuth Credentials

- Create a developer app on [HubSpot Developer Portal](https://developers.hubspot.com/).
- Note your **Client ID**, **Client Secret**, and **Redirect URI**.
- Use them to complete the HubSpot OAuth2 flow.

---

## 📦 Folder Structure

```
/frontend
  └── src
      └── integrations
          ├── airtable.js
          ├── notion.js
          └── hubspot.js      <-- Added logic for HubSpot integration

/backend
  └── integrations
      ├── airtable.py
      ├── notion.py
      └── hubspot.py         <-- OAuth & data fetch logic for HubSpot
```

---

## 📬 Contact

For any issues or questions, reach out to: [recruiting@vectorshift.ai](mailto:recruiting@vectorshift.ai)

---

## 📝 Notes

- You can optionally use your own Airtable and Notion credentials if you want to test those integrations.
- All code is written to follow the structure and patterns of the existing files.
