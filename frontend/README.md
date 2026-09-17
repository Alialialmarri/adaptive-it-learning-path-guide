# Adaptive Learning App Frontend

This is the Angular frontend for the Adaptive IT Learning Path Guide.

## Setup Instructions

Since this project was initialized manually (due to environment restrictions), please follow these steps to get started:

1.  **Install Dependencies:**
    Ensure you have Node.js and NPM installed.
    Run `npm install` in this directory to install all Angular dependencies listed in `package.json`.

2.  **Run the Application:**
    Run `npm start` or `ng serve` to launch the development server.
    Navigate to `http://localhost:4200/`.

## Project Structure

- `src/app/features/`: Contains the main feature modules.
  - `auth/`: Login and registration components.
  - `dashboard/`: Main layout component.
  - `track-map/`: Curriculum visualization component.
  - `chat/`: AI tutor chat interface.
- `src/environments/`: Configuration for different environments (dev/prod).

## Key Components

- **TrackMapComponent**: Visualizes the learning modules (Brilliant-style).
- **ChatInterfaceComponent**: Handles the RAG-powered chat interactions.
- **DashboardComponent**: Manages the split-screen layout.
