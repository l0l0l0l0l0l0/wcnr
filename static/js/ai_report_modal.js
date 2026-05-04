/* AI档案模态框逻辑 */

let _aiReportCacheKey = null;
let _aiReportPollTimer = null;
let _aiReportCurrentIdCard = null;

async function openAiReport(idCard) {
  _aiReportCurrentIdCard = idCard;
  const overlay = document.getElementById('aiReportOverlay');
  const body = document.getElementById('aiReportBody');
  const title = document.getElementById('aiReportTitle');

  title.textContent = 'AI档案';
  body.innerHTML = '<div class="ai-report-loading"><i class="fas fa-spinner fa-spin"></i><span>加载中...</span></div>';
  overlay.classList.add('show');

  try {
    const res = await Auth.authFetch(`${API_BASE}/api/ai-report/person/${idCard}/db`);
    const result = await res.json();
    if (!result.success) {
      body.innerHTML = '<div class="ai-report-error">加载数据失败：' + (result.message || '未知错误') + '</div>';
      return;
    }

    _aiReportCacheKey = result.cache_key;
    title.textContent = `${result.data.basic_info.name} - AI档案`;
    renderAiReportDbData(result.data);

    if (result.llm_status === 'cached') {
      fetchCachedLlmResult();
    } else {
      startLlmGeneration(idCard);
    }
  } catch (e) {
    console.error('加载AI档案失败:', e);
    body.innerHTML = '<div class="ai-report-error">加载失败，请重试</div>';
  }
}

function _fillFields(container, data) {
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

function _buildInfoGridHtml(fields) {
  return fields.map(([label, field, value]) =>
    `<div class="ai-report-info-row"><span class="label">${label}：</span><span class="value" data-field="${field}">${value || 'xxx'}</span></div>`
  ).join('');
}

function renderAiReportDbData(data) {
  const body = document.getElementById('aiReportBody');
  const basic = data.basic_info;
  const report = data.patrol_report;

  const basicFields = [
    ['姓名', 'name'], ['性别', 'gender'], ['出生日期', 'birth_date'],
    ['年龄', 'age'], ['身份证号', 'id_card'], ['籍贯', 'native_place'],
    ['户籍地址', 'household_address'], ['居住地', 'residence'],
    ['学历', 'education'], ['学校', 'school'],
    ['入学日期', 'enrollment_date'], ['毕业日期', 'graduation_date'],
    ['所属分局', 'subordinate_bureau'], ['所辖派出所', 'police_station'],
    ['人员类型', 'person_type_tag']
  ];

  const deliveryFields = [
    ['送生时间', 'time'], ['送生单位', 'unit']
  ];

  const otherFields = [
    ['是否严重不良行为未成年人', 'is_serious_bad_minor'], ['本人电话', 'personal_phone'],
    ['监护人电话', 'guardian_phone'], ['备注', 'remarks'],
    ['不良行为记录', 'bad_behavior_records'], ['飙车炸街行为', 'racing_behavior'],
    ['分析手机号', 'analysis_phone']
  ];

  const reportBasicFields = [
    ['姓名', 'name'], ['性别', 'gender'], ['年龄', 'age'],
    ['身份证号', 'id_card'], ['籍贯', 'native_place'],
    ['户籍地址', 'household_address'], ['居住地', 'residence'],
    ['学历', 'education'], ['学校', 'school'],
    ['入学日期', 'enrollment_date'], ['毕业日期', 'graduation_date'],
    ['所属分局', 'subordinate_bureau'], ['所辖派出所', 'police_station'],
    ['人员类型', 'person_type_tag']
  ];

  // Guardians
  let guardiansHtml = '';
  if (data.guardians && data.guardians.length > 0) {
    guardiansHtml = data.guardians.map(g => {
      const type = g.guardian_type || '监护人';
      return `<div class="guardian-block">
        <div class="ai-report-info-row"><span class="label">${type}：</span><span class="value">${g.name || 'xxx'}</span></div>
        <div class="ai-report-info-row"><span class="label">联系方式：</span><span class="value">${g.contact || ''}</span></div>
        <div class="ai-report-info-row"><span class="label">身份证：</span><span class="value">${g.id_card_number || ''}</span></div>
        <div class="ai-report-info-row"><span class="label">关系：</span><span class="value">${g.relation || ''}</span></div>
        ${g.address ? `<div class="ai-report-info-row"><span class="label">居住地：</span><span class="value">${g.address}</span></div>` : ''}
      </div>`;
    }).join('');
  } else {
    guardiansHtml = '<div class="ai-report-info-row"><span class="value">暂无监护人信息</span></div>';
  }

  // Alert records
  let alertRecordsHtml = '';
  if (data.alert_records && data.alert_records.length > 0) {
    alertRecordsHtml = data.alert_records.map(r =>
      `<div class="alert-record">
        <div class="ai-report-info-row"><span class="label">${r.time}</span></div>
        <div class="ai-report-info-row indent"><span class="label">地点：</span><span class="value">${r.location}</span></div>
        <div class="ai-report-info-row indent"><span class="label">情况：</span><span class="value">${r.situation}</span></div>
        <div class="ai-report-info-row indent"><span class="label">处理：</span><span class="value">${r.detail}</span></div>
      </div>`
    ).join('');
  } else {
    alertRecordsHtml = '<div class="ai-report-info-row"><span class="value">暂无历史预警记录</span></div>';
  }

  // Report history records
  let reportHistoryHtml = '';
  if (report.history_records && report.history_records.length > 0) {
    reportHistoryHtml = report.history_records.map(r =>
      `<div class="history-record">
        <div class="ai-report-info-row"><span class="label">${r.time}</span></div>
        <div class="ai-report-info-row indent"><span class="label">地点：</span><span class="value">${r.location}</span></div>
        <div class="ai-report-info-row indent"><span class="label">情况：</span><span class="value">${r.situation}</span></div>
        <div class="ai-report-info-row indent"><span class="label">处理：</span><span class="value">${r.action}</span></div>
      </div>`
    ).join('');
  }

  const loadingSpinner = '<div class="ai-report-llm-loading"><i class="fas fa-spinner fa-spin"></i><span>AI分析生成中...</span></div>';

  body.innerHTML = `
    <div class="ai-report-content">
      <!-- 个人简介 -->
      <div class="ai-report-section">
        <div class="ai-report-section-title">个人简介</div>
        <div class="ai-report-subsection">
          <div class="ai-report-subsection-title">基础信息</div>
          <div class="ai-report-info-grid" id="modalBasicInfo">
            ${basicFields.map(([label, field]) =>
              `<div class="ai-report-info-row"><span class="label">${label}：</span><span class="value" data-field="${field}">${basic[field] || 'xxx'}</span></div>`
            ).join('')}
          </div>
        </div>
        <div class="ai-report-subsection">
          <div class="ai-report-subsection-title">监护人信息</div>
          <div id="modalGuardiansInfo">${guardiansHtml}</div>
        </div>
        <div class="ai-report-subsection">
          <div class="ai-report-subsection-title">送生信息</div>
          <div class="ai-report-info-grid" id="modalDeliveryInfo">
            ${deliveryFields.map(([label, field]) =>
              `<div class="ai-report-info-row"><span class="label">${label}：</span><span class="value" data-field="${field}">${data.delivery_info[field] || 'xxx'}</span></div>`
            ).join('')}
          </div>
        </div>
        <div class="ai-report-subsection">
          <div class="ai-report-subsection-title">其他信息</div>
          <div class="ai-report-info-grid" id="modalOtherInfo">
            ${otherFields.map(([label, field]) =>
              `<div class="ai-report-info-row"><span class="label">${label}：</span><span class="value" data-field="${field}">${data.other_info[field] || 'xxx'}</span></div>`
            ).join('')}
          </div>
        </div>
      </div>

      <!-- 历史预警反馈信息 -->
      <div class="ai-report-section">
        <div class="ai-report-section-title">历史预警反馈信息</div>
        <div id="modalAlertRecords">${alertRecordsHtml}</div>
      </div>

      <!-- 巡逻防范报告 -->
      <div class="ai-report-section">
        <div class="ai-report-section-title">巡逻防范报告</div>

        <div class="ai-report-subsection">
          <div class="ai-report-subsection-title">一、基本信息</div>
          <div class="ai-report-info-grid" id="modalReportBasicInfo">
            ${reportBasicFields.map(([label, field]) =>
              `<div class="ai-report-info-row"><span class="label">${label}：</span><span class="value" data-field="${field}">${report.basic_info[field] || 'xxx'}</span></div>`
            ).join('')}
          </div>
        </div>

        <div class="ai-report-subsection">
          <div class="ai-report-subsection-title">二、历史预警记录</div>
          <div id="modalReportHistoryRecords">${reportHistoryHtml}</div>
        </div>

        <div class="ai-report-subsection">
          <div class="ai-report-subsection-title">三、同行人信息</div>
          <div class="ai-report-text-content" id="modalCompanionInfo">${report.companion_info}</div>
        </div>

        <div class="ai-report-subsection ai-report-llm-section">
          <div class="ai-report-subsection-title">四、行为模式和潜在风险</div>
          <div id="modalRiskAnalysis">
            <div class="ai-report-info-row"><span class="label">频繁出现地点：</span><span class="value" id="risk-frequent"></span></div>
            <div class="ai-report-info-row"><span class="label">时间规律：</span><span class="value" id="risk-time"></span></div>
            <div class="ai-report-info-row"><span class="label">家庭监管：</span><span class="value" id="risk-family"></span></div>
            <div class="ai-report-info-row"><span class="label">潜在风险：</span><span class="value" id="risk-potential"></span></div>
            ${loadingSpinner}
          </div>
        </div>

        <div class="ai-report-subsection ai-report-llm-section">
          <div class="ai-report-subsection-title">五、巡逻防范建议</div>
          <div id="modalSuggestions" class="suggestion-list">
            ${loadingSpinner}
          </div>
        </div>

        <div class="ai-report-subsection ai-report-llm-section">
          <div class="ai-report-subsection-title">结论</div>
          <div class="ai-report-text-content" id="modalConclusion">
            ${loadingSpinner}
          </div>
        </div>
      </div>
    </div>
  `;
}

async function fetchCachedLlmResult() {
  if (!_aiReportCacheKey) return;
  try {
    const res = await Auth.authFetch(`${API_BASE}/api/ai-report/llm-result/${_aiReportCacheKey}`);
    const result = await res.json();
    if (result.status === 'done' && result.data) {
      renderAiReportLlmData(result.data);
    }
  } catch (e) {
    console.error('获取LLM缓存结果失败:', e);
  }
}

async function startLlmGeneration(idCard) {
  try {
    const res = await Auth.authFetch(`${API_BASE}/api/ai-report/person/${idCard}/llm`);
    const result = await res.json();
    if (result.status === 'done' && result.data) {
      renderAiReportLlmData(result.data);
    } else if (result.status === 'pending') {
      _aiReportCacheKey = result.cache_key;
      startPolling();
    }
  } catch (e) {
    console.error('启动LLM生成失败:', e);
    showLlmError();
  }
}

function startPolling() {
  stopPolling();
  _aiReportPollTimer = setInterval(pollLlmResult, 3000);
}

function stopPolling() {
  if (_aiReportPollTimer) {
    clearInterval(_aiReportPollTimer);
    _aiReportPollTimer = null;
  }
}

async function pollLlmResult() {
  if (!_aiReportCacheKey) return;
  try {
    const res = await Auth.authFetch(`${API_BASE}/api/ai-report/llm-result/${_aiReportCacheKey}`);
    const result = await res.json();
    if (result.status === 'done') {
      stopPolling();
      renderAiReportLlmData(result.data);
    } else if (result.status === 'error') {
      stopPolling();
      showLlmError();
    }
  } catch (e) {
    // 网络错误，继续轮询
    console.error('轮询LLM结果失败:', e);
  }
}

function renderAiReportLlmData(llmData) {
  if (!llmData) return;

  // Risk analysis
  const riskEl = document.getElementById('modalRiskAnalysis');
  if (riskEl && llmData.risk_analysis) {
    const ra = llmData.risk_analysis;
    const loading = riskEl.querySelector('.ai-report-llm-loading');
    if (loading) loading.remove();
    document.getElementById('risk-frequent').textContent = ra.frequent_places;
    document.getElementById('risk-time').textContent = ra.time_pattern;
    document.getElementById('risk-family').textContent = ra.family_supervision;
    document.getElementById('risk-potential').textContent = ra.potential_risk;
  }

  // Suggestions
  const sugEl = document.getElementById('modalSuggestions');
  if (sugEl && llmData.suggestions) {
    const labels = ['加强重点区域巡逻：', '社区联动：', '家庭监督：', '心理辅导：', '定期回访：'];
    sugEl.innerHTML = llmData.suggestions.map((s, idx) =>
      `<p><strong>${labels[idx] || '建议：'}</strong>${s}</p>`
    ).join('');
  }

  // Conclusion
  const conEl = document.getElementById('modalConclusion');
  if (conEl && llmData.conclusion) {
    conEl.innerHTML = `<p>${llmData.conclusion}</p>`;
  }

  // Mark sections as loaded
  document.querySelectorAll('.ai-report-llm-section').forEach(el => {
    el.classList.add('ai-report-llm-loaded');
  });
}

function showLlmError() {
  document.querySelectorAll('.ai-report-llm-loading').forEach(el => {
    el.className = 'ai-report-llm-error';
    el.innerHTML = '<i class="fas fa-exclamation-triangle"></i><span>AI分析生成失败</span><button onclick="retryAiReportLlm()">重试</button>';
  });
}

function retryAiReportLlm() {
  // 重置LLM区域为loading状态
  document.querySelectorAll('.ai-report-llm-error').forEach(el => {
    el.className = 'ai-report-llm-loading';
    el.innerHTML = '<i class="fas fa-spinner fa-spin"></i><span>AI分析生成中...</span>';
  });
  if (_aiReportCurrentIdCard) {
    startLlmGeneration(_aiReportCurrentIdCard);
  }
}

function closeAiReport() {
  const overlay = document.getElementById('aiReportOverlay');
  overlay.classList.remove('show');
  stopPolling();
  _aiReportCacheKey = null;
  _aiReportCurrentIdCard = null;
}

// 点击遮罩层关闭
document.addEventListener('DOMContentLoaded', () => {
  const overlay = document.getElementById('aiReportOverlay');
  if (overlay) {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) closeAiReport();
    });
  }
});
