document.addEventListener("DOMContentLoaded", () => {
    const html = document.documentElement;
    const themeToggle = document.getElementById("themeToggle");
    const savedTheme = localStorage.getItem("storyTheme") || "light";

    const setTheme = (theme) => {
        html.setAttribute("data-bs-theme", theme);
        localStorage.setItem("storyTheme", theme);
        if (themeToggle) {
            themeToggle.innerHTML = theme === "dark"
                ? '<i class="bi bi-sun"></i>'
                : '<i class="bi bi-moon-stars"></i>';
        }
    };

    setTheme(savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener("click", () => {
            const nextTheme = html.getAttribute("data-bs-theme") === "dark" ? "light" : "dark";
            setTheme(nextTheme);
        });
    }

    document.querySelectorAll("[data-bs-toggle='tooltip']").forEach((element) => {
        new bootstrap.Tooltip(element);
    });

    const keywordBox = document.getElementById("keywords");
    const keywordCounter = document.getElementById("keywordCounter");
    if (keywordBox && keywordCounter) {
        const updateCounter = () => {
            keywordCounter.textContent = `${keywordBox.value.length}/200`;
        };
        keywordBox.addEventListener("input", updateCounter);
        updateCounter();
    }

    const storyForm = document.getElementById("storyForm");
    const generateBtn = document.getElementById("generateBtn");
    if (storyForm && generateBtn) {
        storyForm.addEventListener("submit", () => {
            generateBtn.disabled = true;
            generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Generating...';
        });
    }

    const copyButton = document.getElementById("copyStoryBtn");
    const storyText = document.getElementById("storyText");
    if (copyButton && storyText) {
        copyButton.addEventListener("click", async () => {
            try {
                await navigator.clipboard.writeText(storyText.innerText.trim());
                copyButton.innerHTML = '<i class="bi bi-check2"></i> Copied';
                setTimeout(() => {
                    copyButton.innerHTML = '<i class="bi bi-copy"></i> Copy';
                }, 1400);
            } catch (error) {
                copyButton.innerHTML = '<i class="bi bi-exclamation-circle"></i> Failed';
            }
        });
    }

    document.querySelectorAll("form[data-confirm]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!window.confirm(form.dataset.confirm)) {
                event.preventDefault();
            }
        });
    });
});
