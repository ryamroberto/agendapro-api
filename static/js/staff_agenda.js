/**
 * Lógica do Painel da Agenda do Prestador (Staff Only - Vanilla JS)
 */

document.addEventListener('DOMContentLoaded', () => {
    const agendaListContainer = document.getElementById('agenda-list');
    const filterDateInput = document.getElementById('filter-date');
    const filterBtn = document.getElementById('btn-filter-date');
    const clearFilterBtn = document.getElementById('btn-clear-filter');
    const alertBox = document.getElementById('agenda-alert');

    loadAgenda();

    filterBtn.addEventListener('click', () => {
        loadAgenda(filterDateInput.value);
    });

    clearFilterBtn.addEventListener('click', () => {
        filterDateInput.value = '';
        loadAgenda();
    });

    async function loadAgenda(dateStr = '') {
        agendaListContainer.innerHTML = '<p style="color: var(--color-text-muted);">Carregando atendimentos...</p>';
        try {
            let url = '/api/appointments/';
            if (dateStr) {
                url += `?date=${dateStr}`;
            }

            const res = await apiFetch(url);
            if (!res.ok) throw new Error('Erro ao carregar atendimentos da agenda.');
            const appointments = await res.json();

            agendaListContainer.innerHTML = '';
            if (appointments.length === 0) {
                agendaListContainer.innerHTML = `
                    <p style="color: var(--color-text-muted); padding: var(--space-6); text-align: center;">
                        Nenhum atendimento encontrado ${dateStr ? 'para a data ' + formatDate(dateStr) : ''}.
                    </p>
                `;
                return;
            }

            const tableWrapper = document.createElement('div');
            tableWrapper.className = 'table-responsive';

            let rowsHtml = '';
            appointments.forEach(appt => {
                let actionButtons = '';

                if (appt.status === 'pending') {
                    actionButtons = `
                        <button class="btn btn-primary btn-sm btn-action" data-id="${appt.id}" data-status="confirmed" aria-label="Confirmar agendamento de ${escapeHtml(appt.client_username)}">Confirmar</button>
                        <button class="btn btn-danger btn-sm btn-action" data-id="${appt.id}" data-status="cancelled" aria-label="Cancelar agendamento de ${escapeHtml(appt.client_username)}">Cancelar</button>
                    `;
                } else if (appt.status === 'confirmed') {
                    actionButtons = `
                        <button class="btn btn-success btn-sm btn-action" data-id="${appt.id}" data-status="completed" aria-label="Concluir agendamento de ${escapeHtml(appt.client_username)}">Concluir</button>
                        <button class="btn btn-danger btn-sm btn-action" data-id="${appt.id}" data-status="cancelled" aria-label="Cancelar agendamento de ${escapeHtml(appt.client_username)}">Cancelar</button>
                    `;
                } else {
                    actionButtons = `<span style="color: var(--color-text-muted); font-size: var(--font-size-xs); font-weight: var(--font-weight-medium);">Finalizado</span>`;
                }

                rowsHtml += `
                    <tr>
                        <td><strong>${appt.time.substring(0, 5)}</strong></td>
                        <td>${formatDate(appt.date)}</td>
                        <td>
                            <strong>${escapeHtml(appt.client_username)}</strong>
                            ${appt.notes ? '<br><small style="color: var(--color-text-muted);">' + escapeHtml(appt.notes) + '</small>' : ''}
                        </td>
                        <td>${escapeHtml(appt.service_name)} (R$ ${parseFloat(appt.service_price).toFixed(2)})</td>
                        <td><span class="badge badge-${appt.status}">${escapeHtml(appt.status_display)}</span></td>
                        <td><div style="display: flex; gap: var(--space-2); flex-wrap: wrap;">${actionButtons}</div></td>
                    </tr>
                `;
            });

            tableWrapper.innerHTML = `
                <table class="table" aria-label="Tabela de atendimentos da agenda">
                    <thead>
                        <tr>
                            <th>Horário</th>
                            <th>Data</th>
                            <th>Cliente</th>
                            <th>Serviço</th>
                            <th>Status</th>
                            <th>Ações do Prestador</th>
                        </tr>
                    </thead>
                    <tbody>${rowsHtml}</tbody>
                </table>
            `;

            agendaListContainer.appendChild(tableWrapper);

            // Adiciona listeners aos botões de ação de status
            document.querySelectorAll('.btn-action').forEach(btn => {
                btn.addEventListener('click', () => {
                    const id = btn.getAttribute('data-id');
                    const newStatus = btn.getAttribute('data-status');
                    handleStatusChange(id, newStatus);
                });
            });

        } catch (err) {
            showAlert(err.message, 'error');
        }
    }

    async function handleStatusChange(id, newStatus) {
        try {
            const res = await apiFetch(`/api/appointments/${id}/status/`, {
                method: 'PATCH',
                body: JSON.stringify({ status: newStatus })
            });
            const data = await res.json();

            if (res.ok) {
                showAlert(`Status do agendamento atualizado para "${data.appointment.status_display}".`, 'success');
                loadAgenda(filterDateInput.value);
            } else {
                showAlert(data.status ? data.status[0] : (data.detail || 'Erro ao alterar status.'), 'error');
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
