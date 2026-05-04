/* AI档案页面逻辑 */

let currentPersonIdCard = '';

async function loadPersons(initialIdCard) {
    try {
        const res = await Auth.authFetch(`${API_BASE}/api/ai-report/persons`);
        const data = await res.json();
        if (data.success) {
            const select = document.getElementById('person-select');
            select.innerHTML = '<option value="">请选择人员</option>';
            data.data.forEach(p => {
                const option = document.createElement('option');
                option.value = p.id_card_number;
                option.textContent = `${p.name} (${p.id_card_number})`;
                select.appendChild(option);
            });
            if (initialIdCard) {
                select.value = initialIdCard;
                loadPersonDetail(initialIdCard);
            } else if (data.data.length > 0) {
                select.value = data.data[0].id_card_number;
                loadPersonDetail(data.data[0].id_card_number);
            }
            select.addEventListener('change', (e) => {
                if (e.target.value) {
                    loadPersonDetail(e.target.value);
                }
            });
        }
    } catch (e) {
        console.error('加载人员列表失败:', e);
    }
}

async function loadPersonDetail(idCard) {
    currentPersonIdCard = idCard;
    try {
        const res = await Auth.authFetch(`${API_BASE}/api/ai-report/person/${idCard}`);
        const result = await res.json();
        if (result.success) {
            renderData(result.data);
        } else {
            alert('加载数据失败: ' + (result.message || '未知错误'));
        }
    } catch (e) {
        console.error('加载人员详情失败:', e);
    }
}

function renderData(data) {
    const basic = data.basic_info;
    const report = data.patrol_report;

    document.getElementById('page-title').textContent = `${basic.name}-AI档案`;

    fillFields(document.getElementById('basic-info'), basic);

    // 监护人信息
    const guardiansContainer = document.getElementById('guardians-info');
    guardiansContainer.innerHTML = '';
    if (data.guardians && data.guardians.length > 0) {
        data.guardians.forEach(g => {
            const gDiv = document.createElement('div');
            gDiv.className = 'guardian-block';
            const type = g.guardian_type || '监护人';
            gDiv.innerHTML = `
                <div class="ai-report-info-row"><span class="label">${type}：</span><span class="value">${g.name || 'xxx'}</span></div>
                <div class="ai-report-info-row"><span class="label">联系方式：</span><span class="value">${g.contact || ''}</span></div>
                <div class="ai-report-info-row"><span class="label">身份证：</span><span class="value">${g.id_card_number || ''}</span></div>
                <div class="ai-report-info-row"><span class="label">关系：</span><span class="value">${g.relation || ''}</span></div>
                ${g.address ? `<div class="ai-report-info-row"><span class="label">居住地：</span><span class="value">${g.address}</span></div>` : ''}
            `;
            guardiansContainer.appendChild(gDiv);
        });
    } else {
        guardiansContainer.innerHTML = '<div class="ai-report-info-row"><span class="value">暂无监护人信息</span></div>';
    }

    fillFields(document.getElementById('delivery-info'), data.delivery_info);
    fillFields(document.getElementById('other-info'), data.other_info);

    // 历史预警反馈信息
    const alertContainer = document.getElementById('alert-records');
    alertContainer.innerHTML = '';
    if (data.alert_records && data.alert_records.length > 0) {
        data.alert_records.forEach(r => {
            const rDiv = document.createElement('div');
            rDiv.className = 'alert-record';
            rDiv.innerHTML = `
                <div class="ai-report-info-row"><span class="label">${r.time}</span></div>
                <div class="ai-report-info-row indent"><span class="label">地点：</span><span class="value">${r.location}</span></div>
                <div class="ai-report-info-row indent"><span class="label">情况：</span><span class="value">${r.situation}</span></div>
                <div class="ai-report-info-row indent"><span class="label">处理：</span><span class="value">${r.detail}</span></div>
            `;
            alertContainer.appendChild(rDiv);
        });
    } else {
        alertContainer.innerHTML = '<div class="ai-report-info-row"><span class="value">暂无历史预警记录</span></div>';
    }

    // 巡逻防范报告
    fillFields(document.getElementById('report-basic-info'), report.basic_info);

    const reportHistoryContainer = document.getElementById('report-history-records');
    reportHistoryContainer.innerHTML = '';
    if (report.history_records && report.history_records.length > 0) {
        report.history_records.forEach(r => {
            const rDiv = document.createElement('div');
            rDiv.className = 'history-record';
            rDiv.innerHTML = `
                <div class="ai-report-info-row"><span class="label">${r.time}</span></div>
                <div class="ai-report-info-row indent"><span class="label">地点：</span><span class="value">${r.location}</span></div>
                <div class="ai-report-info-row indent"><span class="label">情况：</span><span class="value">${r.situation}</span></div>
                <div class="ai-report-info-row indent"><span class="label">处理：</span><span class="value">${r.action}</span></div>
            `;
            reportHistoryContainer.appendChild(rDiv);
        });
    }

    document.getElementById('companion-info').textContent = report.companion_info;

    document.getElementById('risk-frequent').textContent = report.risk_analysis.frequent_places;
    document.getElementById('risk-time').textContent = report.risk_analysis.time_pattern;
    document.getElementById('risk-family').textContent = report.risk_analysis.family_supervision;
    document.getElementById('risk-potential').textContent = report.risk_analysis.potential_risk;

    const sugContainer = document.getElementById('suggestions');
    sugContainer.innerHTML = '';
    report.suggestions.forEach((s, idx) => {
        const p = document.createElement('p');
        const labels = ['加强重点区域巡逻：', '社区联动：', '家庭监督：', '心理辅导：', '定期回访：'];
        p.innerHTML = `<strong>${labels[idx] || '建议：'}</strong>${s}`;
        sugContainer.appendChild(p);
    });

    document.getElementById('conclusion').textContent = report.conclusion;
}

function fillFields(container, data) {
    if (!data) return;
    container.querySelectorAll('[data-field]').forEach(el => {
        const field = el.getAttribute('data-field');
        if (data[field] !== undefined && data[field] !== null && data[field] !== '') {
            el.textContent = data[field];
        } else {
            el.textContent = 'xxx';
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const initialIdCard = params.get('person_id_card');
    loadPersons(initialIdCard);
});
