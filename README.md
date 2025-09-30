# **Mie Novel-app FastAPI Backend** 📚
a RESTful API for a novel application. This backend manages users (including administrators), novel content (books, chapters, and pages), and user interactions like bookmarks and likes. It features **JWT-based authentication** for both users and admins, supporting standard credentials and Google sign-in.

## Overview

The **Mie Novel-app FastAPI Backend** provides the core API infrastructure for the "Mie Novel-app," a platform for reading novels. It offers a comprehensive set of RESTful endpoints to handle **user management**, **admin control**, and **novel content management** (books, chapters, pages). Key features include robust **JWT-based authentication** for secure access, supporting both traditional login and Google sign-in, along with token refresh capabilities.

-----

## Features ✨

  * **User Management**: Sign-up, sign-in, retrieve details, update profiles, and manage password changes.
  * **Admin Management**: Separate sign-up/sign-in, invitation system, details retrieval, and admin-level user management (e.g., updating user status).
  * **Authentication**: Secure access via **JWT Bearer tokens** with refresh token support.
  * **Content Management (Admin Privelege)**: CRUD operations for **Books**, **Chapters**, and **Pages**.
  * **User Interactions**: Endpoints for managing user **Bookmarks** and **Likes** on chapters.
  * **Comments**: Users can comment on chapters, and both users and admins can manage comments (delete/update).
  * **Payment Bundles**: Endpoints to create, retrieve, update, and delete payment bundles (admin-only).
  * **Health Check**: A simple endpoint to check API operational status.

-----

## API Structure

The API is structured around different functional areas, accessible via the base path `/api/v1`.

### 🔑 Authentication & Users

| Endpoint | Summary | Security | Role |
| :--- | :--- | :--- | :--- |
| `/user/sign-up` | Register a new user. | None | User |
| `/user/sign-in` | Log in a user. | None | User |
| `/user/refresh` | Get a new access token using a refresh token. | Bearer Token | User |
| `/user/details` | Retrieve the authenticated user's details. | Bearer Token | User |
| `/user/initiate/change-password` | Start the password change process. | None | User |
| `/user/conclude/change-password` | Complete the password change process. | None | User |
| `/user/update` | Update the authenticated user's profile. | Bearer Token | User |

### 👑 Admin Endpoints (Requires Admin Token)

| Endpoint | Summary | Security | Role |
| :--- | :--- | :--- | :--- |
| `/admin/sign-up` | Register a new admin (likely via invite). | None | Admin |
| `/admin/sign-in` | Log in an admin. | None | Admin |
| `/admin/invite` | Invite a new admin. | Bearer Token | Admin |
| `/admin/details` | Get authenticated admin details. | Bearer Token | Admin |
| `/admin/all/details` | Get all admin details. | Bearer Token | Admin |
| `/user/all/user-details` | Get data for all users. | Bearer Token | Admin |
| `/user/{userId}/status/{new_status}` | Update a user's status (active, suspended, inactive). | Bearer Token | Admin |
| `/admin/dashboardAnalytics` | Retrieve dashboard analytics. | Bearer Token | Admin |

### 📖 Content Management (Books, Chapters, Pages)

| Endpoint | Summary | Security | Role |
| :--- | :--- | :--- | :--- |
| `/book/get` | Get all available books. | Bearer Token | User/Admin |
| `/book/create` | Create a new book. | Bearer Token | Admin |
| `/book/delete/{bookId}` | Delete a book. | Bearer Token | Admin |
| `/chapter/create` | Create a new chapter. | Bearer Token | Admin |
| `/chapter/user/get/allChapters/{bookId}` | Get all chapters for a book. | Bearer Token | User |
| `/page/create/{bookId}` | Create a new page. | Bearer Token | Admin |
| `/page/get/{chapterId}` | Get all pages for a chapter. | Bearer Token | User/Admin |

### 🔖 User Interactions (Bookmarks, Likes, Comments)

| Endpoint | Summary | Security | Role |
| :--- | :--- | :--- | :--- |
| `/bookmark/create` | Add a new bookmark. | None | User |
| `/bookmark/get/{userId}` | Get a user's bookmarks. | None | User |
| `/like/create` | Like a chapter. | Bearer Token | User |
| `/like/remove/{likeId}` | Unlike a chapter. | Bearer Token | User |
| `/comment/create` | Post a comment on a chapter. | Bearer Token | User |
| `/comment/get/{chapterId}` | Get all comments for a chapter. | None | User/Admin |

-----

## Authentication

Authentication is handled via **JWT Bearer Tokens**.

1.  **Sign In**: Send credentials to `/user/sign-in` or `/admin/sign-in`. The response will contain an **Access Token** and a **Refresh Token**.
2.  **Access Token Usage**: Include the Access Token in the `Authorization` header for all protected endpoints in the format `Authorization: Bearer <Access Token>`.
3.  **Token Refresh**: When the Access Token expires, use the Refresh Token at `/user/refresh` or `/admin/refresh` to obtain a new Access Token.

-----

## Getting Started (Deployment)

*(This section assumes a standard FastAPI/Python deployment setup. You'll need to fill in specific environment variables and setup steps for a real deployment.)*

1.  **Clone the Repository**
2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure Environment Variables**
    You will need to set up environment variables for the database connection, JWT secret key, and potentially Google sign-in configuration.
      * `DATABASE_URL`
      * `JWT_SECRET_KEY`
      * `ALGORITHM`
      * `ACCESS_TOKEN_EXPIRE_MINUTES`
4.  **Run the Server**
    ```bash
    uvicorn main:app --reload
    ```

-----

## API Documentation

Once the server is running, the OpenAPI interactive documentation (Swagger UI) will typically be available at:

  * **URL**: `/docs` (e.g., `http://127.0.0.1:8000/docs`)

You can use this interface to explore all endpoints, view required schemas, and test API calls directly.