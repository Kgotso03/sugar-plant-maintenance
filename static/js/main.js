/**
 * Sugar Plant Predictive Maintenance System
 * Main application JavaScript: sidebar navigation, PWA registration, and UI helpers.
 */

document.addEventListener("DOMContentLoaded", function () {
  // ── Sidebar Menu Navigation (Desktop Collapse & Mobile Drawer) ──────────
  const menuToggle = document.getElementById("menuToggle");
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebarOverlay");
  const mainWrapper = document.querySelector(".main-wrapper");

  if (menuToggle && sidebar) {
    // Restore saved desktop collapsed state
    if (window.innerWidth > 900 && localStorage.getItem("sidebar_collapsed") === "1") {
      sidebar.classList.add("collapsed");
      if (mainWrapper) mainWrapper.classList.add("expanded");
    }

    menuToggle.addEventListener("click", function () {
      if (window.innerWidth <= 900) {
        // Mobile drawer toggle
        sidebar.classList.toggle("open");
        if (overlay) overlay.classList.toggle("active");
      } else {
        // Desktop collapse / expand
        sidebar.classList.toggle("collapsed");
        if (mainWrapper) mainWrapper.classList.toggle("expanded");
        const isCollapsed = sidebar.classList.contains("collapsed");
        localStorage.setItem("sidebar_collapsed", isCollapsed ? "1" : "0");
      }
    });

    if (overlay) {
      overlay.addEventListener("click", function () {
        sidebar.classList.remove("open");
        overlay.classList.remove("active");
      });
    }

    const sidebarCloseBtn = document.getElementById("sidebarCloseBtn");
    if (sidebarCloseBtn) {
      sidebarCloseBtn.addEventListener("click", function () {
        sidebar.classList.remove("open");
        if (overlay) overlay.classList.remove("active");
      });
    }

    // Auto-close drawer on mobile when clicking any navigation link
    sidebar.querySelectorAll(".nav-item").forEach(function (link) {
      link.addEventListener("click", function () {
        if (window.innerWidth <= 900) {
          sidebar.classList.remove("open");
          if (overlay) overlay.classList.remove("active");
        }
      });
    });
  }

  // ── Auto-dismiss flash notifications ───────────────────────────────────
  const flashAlerts = document.querySelectorAll(".alert-banner");
  flashAlerts.forEach((alert) => {
    setTimeout(() => {
      alert.style.transition = "opacity 0.4s ease";
      alert.style.opacity = "0";
      setTimeout(() => alert.remove(), 400);
    }, 6000);
  });

  // ── Confirmation prompts on destructive actions ────────────────────────
  document.querySelectorAll("[data-confirm]").forEach((el) => {
    el.addEventListener("click", function (e) {
      const msg = this.getAttribute("data-confirm") || "Are you sure you want to proceed?";
      if (!confirm(msg)) {
        e.preventDefault();
      }
    });
  });

  // ── PWA Service Worker Registration ────────────────────────────────────
  if ("serviceWorker" in navigator && window.location.protocol.startsWith("http")) {
    navigator.serviceWorker.register("/static/sw.js").catch(function (err) {
      console.warn("ServiceWorker registration skipped:", err);
    });
  }
});
