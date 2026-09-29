// Financial Analyzer – theme toggle + small UX helpers

document.addEventListener("DOMContentLoaded", function () {
    // Auto-dismiss alerts
    document.querySelectorAll(".alert-dismissible").forEach(function (alert) {
        setTimeout(function () {
            try {
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                if (bsAlert) bsAlert.close();
            } catch (e) {}
        }, 6000);
    });

    // Theme toggle
    const root = document.documentElement;
    const btn = document.getElementById("themeToggle");
    const icon = document.getElementById("themeIcon");

    function currentTheme() {
        return root.getAttribute("data-bs-theme") === "dark" ? "dark" : "light";
    }

    function setTheme(theme) {
        root.setAttribute("data-bs-theme", theme);
        try {
            localStorage.setItem("fa-theme", theme);
        } catch (e) {}
        if (icon) {
            icon.className = theme === "dark" ? "bi bi-sun" : "bi bi-moon-stars";
        }
    }

    // Sync icon on load
    setTheme(currentTheme());

    if (btn) {
        btn.addEventListener("click", function () {
            setTheme(currentTheme() === "dark" ? "light" : "dark");
        });
    }
});
