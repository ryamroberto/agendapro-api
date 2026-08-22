/**
 * Lógica da Página "Meus Agendamentos" (Vanilla JS)
 */

document.addEventListener('DOMContentLoaded', () => {
    const listContainer = document.getElementById('appointments-list');
    const alertBox = document.getElementById('appointments-alert');

    loadAppointments();

    async function loadAppointments() {
        listContainer.innerHTML = '<p style="color: var(--color-text-muted);">Carregando seus agendamentos...</p>';
        try {
            const res = await apiFetch('/api/appointments/');
            if (!res.ok) throw new Error('Erro ao carregar agendamentos.');
            const appointments = await res.json();

            listContainer.innerHTML = '';
            if (appointments.length === 0) {
                listContainer.innerHTML = `
                    <div style="text-align: center; padding: var(--space-8) var(--space-4);">
                        <p style="color: var(--color-text-muted); margin-bottom: var(--space-4);">Você ainda não possui nenhum agendamento.</p>
                        <a href="/" class="btn btn-primary">Agendar um Serviço</a>
                    </div>
                `;
                return;
            }

            const tableWrapper = document.createElement('div');
            tableWrapper.className = 'table-responsive';
            
            let rowsHtml = '';
            appointments.forEach(appt => {
                const canCancel = appt.status === 'pending' || appt.status === 'confirmed';
                const cancelBtn = canCancel 
                    ? `<button class="btn btn-danger btn-sm cancel-btn" data-id="${appt.id}" aria-label="Cancelar agendamento de ${escapeHtml(appt.service_name)}">Cancelar</button>`
                    : '-';

                rowsHtml += `
                    <tr>
                        <td><strong>${escapeHtml(appt.service_name)}</strong></td>
                        <td>${formatDate(appt.date)}</td>
                        <td><strong>${appt.time.substring(0, 5)}</strong></td>
                        <td>R$ ${parseFloat(appt.service_price).toFixed(2)}</td>
                        <td><span class="badge badge-${appt.status}">${escapeHtml(appt.status_display)}</span></td>
                        <td>${cancelBtn}</td>
                    </tr>
                `;
            });

            tableWrapper.innerHTML = `
                <table class="table" aria-label="Tabela dos meus agendamentos">
                    <thead>
                        <tr>
                            <th>Serviço</th>
                            <th>Data</th>
                            <th>Horário</th>
                            <th>Valor</th>
                            <th>Status</th>
                            <th>Ação</th>
                        </tr>
                    </thead>
                    <tbody>${rowsHtml}</tbody>
                </table>
            `;

            listContainer.appendChild(tableWrapper);

            // Adiciona listeners para botões de cancelamento
            document.querySelectorAll('.cancel-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const id = btn.getAttribute('data-id');
                    handleCancelAppointment(id);
                });
            });

        } catch (err) {
            showAlert(err.message, 'error');
        }
    }

    async function handleCancelAppointment(id) {
        if (!confirm('Deseja realmente cancelar este agendamento?')) {
            return;
        }

        try {
            const res = await apiFetch(`/api/appointments/${id}/cancel/`, {
                method: 'POST'
            });
            const data = await res.json();

            if (res.ok) {
                showAlert('Agendamento cancelado com sucesso. O horário foi liberado.', 'success');
                loadAppointments();
            } else {
                showAlert(data.detail || 'Não foi possível cancelar o agendamento.', 'error');
            }
        } catch (err) {
            showAlert('Erro de comunicação com o servidor.', 'error');
        }
    }

    function formatDate(dateStr) {
        if (!dateStr) return '';
        const parts = dateStr.split('-');
        return `${parts[2]}/${parts[1]}/${parts[0]}`;
    }

    function showAlert(message, type) {
        alertBox.className = `alert alert-${type}`;
        alertBox.textContent = message;
        alertBox.style.display = 'block';
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
