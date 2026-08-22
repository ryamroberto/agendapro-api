/**
 * Lógica da Página de Agendamento (Vanilla JS)
 */

document.addEventListener('DOMContentLoaded', () => {
    const servicesContainer = document.getElementById('services-container');
    const dateInput = document.getElementById('appointment-date');
    const slotsContainer = document.getElementById('slots-container');
    const slotsMessage = document.getElementById('slots-message');
    const notesInput = document.getElementById('appointment-notes');
    const submitBtn = document.getElementById('submit-booking-btn');
    const alertBox = document.getElementById('booking-alert');

    let selectedServiceId = null;
    let selectedTime = null;

    /**
     * Retorna a data no formato YYYY-MM-DD com base no horário local do navegador
     * (evita deslocamento de fuso horário UTC como em toISOString).
     */
    function getLocalDateString(dateObj = new Date()) {
        const year = dateObj.getFullYear();
        const month = String(dateObj.getMonth() + 1).padStart(2, '0');
        const day = String(dateObj.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    // 1. Configura data mínima para hoje no horário local
    const today = getLocalDateString();
    dateInput.min = today;
    dateInput.value = today;

    // 2. Carrega serviços ativos da API
    loadServices();

    // 3. Carrega horários disponíveis para a data inicial
    loadAvailableSlots(today);

    // Event listeners
    dateInput.addEventListener('change', (e) => {
        selectedTime = null;
        updateSubmitButtonState();
        loadAvailableSlots(e.target.value);
    });

    submitBtn.addEventListener('click', handleBookingSubmit);

    async function loadServices() {
        try {
            const res = await apiFetch('/api/services/');
            if (!res.ok) throw new Error('Erro ao carregar serviços.');
            const services = await res.json();

            servicesContainer.innerHTML = '';
            if (services.length === 0) {
                servicesContainer.innerHTML = '<p style="color: var(--color-text-muted);">Nenhum serviço disponível no momento.</p>';
                return;
            }

            services.forEach((service, index) => {
                const card = document.createElement('div');
                card.className = 'service-card';
                if (index === 0) {
                    card.classList.add('selected');
                    selectedServiceId = service.id;
                    updateSubmitButtonState();
                }

                card.innerHTML = `
                    <h3>${escapeHtml(service.name)}</h3>
                    <p style="color: var(--color-text-muted); font-size: var(--font-size-sm); margin-top: var(--space-1);">
                        ${escapeHtml(service.description || 'Duração: ' + service.duration_minutes + ' min')}
                    </p>
                    <div class="service-price">R$ ${parseFloat(service.price).toFixed(2)}</div>
                `;

                card.addEventListener('click', () => {
                    document.querySelectorAll('.service-card').forEach(c => c.classList.remove('selected'));
                    card.classList.add('selected');
                    selectedServiceId = service.id;
                    updateSubmitButtonState();
                });

                servicesContainer.appendChild(card);
            });
        } catch (err) {
            showAlert(err.message, 'error');
        }
    }

    async function loadAvailableSlots(dateStr) {
        slotsContainer.innerHTML = '<p style="color: var(--color-text-muted);">Consultando horários disponíveis...</p>';
        slotsMessage.textContent = '';
        selectedTime = null;
        updateSubmitButtonState();

        try {
            const res = await apiFetch(`/api/available-slots/?date=${dateStr}`);
            const data = await res.json();

            slotsContainer.innerHTML = '';

            if (data.available_slots && data.available_slots.length > 0) {
                data.available_slots.forEach(slot => {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'slot-btn';
                    btn.textContent = slot;

                    btn.addEventListener('click', () => {
                        document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('selected'));
                        btn.classList.add('selected');
                        selectedTime = slot;
                        updateSubmitButtonState();
                    });

                    slotsContainer.appendChild(btn);
                });
            } else {
                slotsContainer.innerHTML = '';
                slotsMessage.textContent = data.message || 'Nenhum horário disponível para esta data.';
            }
        } catch (err) {
            slotsContainer.innerHTML = '';
            slotsMessage.textContent = 'Erro ao consultar horários.';
        }
    }

    function updateSubmitButtonState() {
        if (selectedServiceId && dateInput.value && selectedTime) {
            submitBtn.removeAttribute('disabled');
        } else {
            submitBtn.setAttribute('disabled', 'true');
        }
    }

    async function handleBookingSubmit() {
        if (!selectedServiceId || !dateInput.value || !selectedTime) {
            showAlert('Selecione um serviço, data e horário antes de continuar.', 'error');
            return;
        }

        submitBtn.setAttribute('disabled', 'true');
        submitBtn.textContent = 'Agendando...';
        hideAlert();

        const payload = {
            service: selectedServiceId,
            date: dateInput.value,
            time: selectedTime,
            notes: notesInput.value.trim()
        };

        try {
            const res = await apiFetch('/api/appointments/', {
                method: 'POST',
                body: JSON.stringify(payload)
            });

            const data = await res.json();

            if (res.ok) {
                showAlert('Agendamento realizado com sucesso! Redirecionando...', 'success');
                setTimeout(() => {
                    window.location.href = '/meus-agendamentos/';
                }, 1200);
            } else {
                let errorMsg = 'Erro ao agendar.';
                if (data.time) errorMsg = Array.isArray(data.time) ? data.time[0] : data.time;
                else if (data.date) errorMsg = Array.isArray(data.date) ? data.date[0] : data.date;
                else if (data.detail) errorMsg = data.detail;
                else if (data.non_field_errors) errorMsg = data.non_field_errors[0];

                showAlert(errorMsg, 'error');
                submitBtn.removeAttribute('disabled');
                submitBtn.textContent = 'Confirmar Agendamento';
                loadAvailableSlots(dateInput.value);
            }
        } catch (err) {
            showAlert('Erro de comunicação com o servidor.', 'error');
            submitBtn.removeAttribute('disabled');
            submitBtn.textContent = 'Confirmar Agendamento';
        }
    }

    function showAlert(message, type) {
        alertBox.className = `alert alert-${type}`;
        alertBox.textContent = message;
        alertBox.style.display = 'block';
    }

    function hideAlert() {
        alertBox.style.display = 'none';
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
