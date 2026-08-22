/**
 * Utilitário CSRF e fetch para chamadas assíncronas no Django REST Framework
 */

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function getCSRFToken() {
    // 1. Tenta ler o cookie padrão 'csrftoken'
    const tokenFromCookie = getCookie('csrftoken');
    if (tokenFromCookie) return tokenFromCookie;

    // 2. Fallback: Lê de um input hidden caso exista no DOM
    const inputToken = document.querySelector('[name=csrfmiddlewaretoken]');
    return inputToken ? inputToken.value : '';
}

async function apiFetch(url, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
        ...(options.headers || {})
    };

    const config = {
        ...options,
        headers,
        credentials: 'same-origin' // Envia cookies de sessão
    };

    const response = await fetch(url, config);
    return response;
}
