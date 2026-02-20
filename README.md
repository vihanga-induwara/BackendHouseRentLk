# HouseRentLk Backend

REST API for HouseRentLk platform.

## Prerequisites
- Node.js
- MongoDB (Local or Atlas)

## Setup

1.  **Install Dependencies**
    ```bash
    npm install
    ```

2.  **Environment Variables**
    Create a `.env` file in the root:
    ```
    PORT=5000
    MONGO_URI=mongodb://localhost:27017/houserentlk
    JWT_SECRET=your_secret_key
    ```

3.  **Run Server**
    ```bash
    # Development
    npm run dev (if nodemon installed)
    # Production
    node server.js
    ```

## API Endpoints

### Auth
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

### Listings
- `GET /api/listings`
- `GET /api/listings/:id`
- `POST /api/listings` (Auth required)
- `PUT /api/listings/:id` (Auth required)
- `DELETE /api/listings/:id` (Auth required)
