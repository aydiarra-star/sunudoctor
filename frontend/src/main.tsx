import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, HashRouter } from "react-router-dom";
import { AppRoutes } from "./App";
import { AuthProvider } from "./lib/auth";
import "./index.css";

// Sur GitHub Pages (statique), le routage par hash garantit un HTTP 200 sur
// chaque écran. Sur le déploiement servi par l'API, on garde des URL propres.
const useHashRouter = __HASH_ROUTER__;
const Router = useHashRouter ? HashRouter : BrowserRouter;

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <Router basename={useHashRouter ? undefined : import.meta.env.BASE_URL}>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </Router>
  </React.StrictMode>,
);
