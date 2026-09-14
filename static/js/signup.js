const signupForm = document.getElementById("signupForm");
const message = document.getElementById("message");

signupForm.addEventListener("submit", function (event) {
    const password = document.getElementById("password").value;
    const confirmPassword =
        document.getElementById("confirmPassword").value;

    if (password !== confirmPassword) {
        event.preventDefault();

        message.textContent = "Passwords do not match.";
        message.style.color = "#ef4444";
        return;
    }

    const button = signupForm.querySelector("button");

    button.disabled = true;
    button.textContent = "Creating Account...";
});