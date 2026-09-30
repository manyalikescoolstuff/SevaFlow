# 📱 SevaFlow Frontend Web Application

This is the customer and staff frontend web application for **SevaFlow**, built with React 19, TypeScript, Vite, and Zustand.

---

## 🛠️ Tech Stack

- **Framework:** React 19 + TypeScript
- **Build Tool:** Vite
- **State Management:** Zustand
- **Routing:** React Router v7
- **Linting:** Oxlint

---

## 🚀 How to Run

1. **Install dependencies:**
   ```cmd
   npm install
   ```

2. **Start development server:**
   ```cmd
   npm run dev
   ```

3. **Open application:**
   Navigate to [http://localhost:5173](http://localhost:5173) in your browser.

---

## 🔗 Connected Backend

Ensure the FastAPI backend server is running on `http://localhost:8000`. Refer to the root [`README.md`](../README.md) for complete instructions on running the backend and database setup.

## Live staff integration — 29 September 2026

`/staff` now opens the real staff login and assigned workstation. The original demo
is preserved at `/staff/demo`. See [STAFF_INTEGRATION.md](STAFF_INTEGRATION.md) for
API setup, supported queue actions, retry recovery and isolated browser tests.
The Admin screens and the demo workstation retain their existing mock data.
