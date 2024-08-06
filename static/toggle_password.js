document.getElementById('togglePassword').addEventListener('click', function (e) {
    const passwordInput = document.getElementById('password')
    const icon = e.currentTarget

    const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password'
    passwordInput.setAttribute('type', type)

    icon.classList.toggle('bi-eye')
    icon.classList.toggle('bi-eye-slash')
})