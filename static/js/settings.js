Auth.requireAuth();

async function loadProfile() {
  const res = await Auth.authFetch('/api/users/me');
  const data = await res.json();
  if (!data.success) return;

  const user = data.data;
  document.getElementById('settingUsername').value = user.username || '';
  const roleText = user.role === 'admin' ? '管理员' : '操作员';
  document.getElementById('settingRole').value = roleText;
  document.getElementById('settingStation').value = user.police_station || '--';
  document.getElementById('settingRealName').value = user.real_name || '';

  document.getElementById('avatarName').textContent = user.real_name || user.username || '--';
  document.getElementById('avatarRole').textContent = roleText;
}

async function saveSettings() {
  const realName = document.getElementById('settingRealName').value.trim();
  const oldPw = document.getElementById('settingOldPassword').value;
  const newPw = document.getElementById('settingNewPassword').value;
  const confirmPw = document.getElementById('settingConfirmPassword').value;

  const body = {};

  if (realName) {
    body.real_name = realName;
  }

  if (oldPw || newPw || confirmPw) {
    if (!oldPw) { showMsg('请输入原密码', 'error'); return; }
    if (!newPw || newPw.length < 6) { showMsg('新密码至少6位', 'error'); return; }
    if (newPw !== confirmPw) { showMsg('两次输入的新密码不一致', 'error'); return; }
    body.old_password = oldPw;
    body.password = newPw;
  }

  if (!body.real_name && !body.old_password) {
    showMsg('请修改信息后再保存', 'error');
    return;
  }

  const res = await Auth.authFetch('/api/users/me', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  const data = await res.json();
  if (data.success) {
    if (body.real_name) {
      const stored = Auth.getUser();
      if (stored) {
        stored.real_name = body.real_name;
        Auth.setUser(stored);
      }
      Auth.initHeader();
      document.getElementById('avatarName').textContent = body.real_name;
    }
    if (body.password) {
      document.getElementById('settingOldPassword').value = '';
      document.getElementById('settingNewPassword').value = '';
      document.getElementById('settingConfirmPassword').value = '';
    }
    showMsg('保存成功', 'success');
  } else {
    showMsg(data.message || '保存失败', 'error');
  }
}

function showMsg(message, type) {
  const el = document.getElementById('settingsMsg');
  if (!el) return;
  el.textContent = message;
  el.className = 'settings-msg ' + (type === 'error' ? 'error' : 'success');
  el.style.display = 'block';
  setTimeout(() => { el.style.display = 'none'; }, 3000);
}

loadProfile();
