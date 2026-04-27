/**
 * 共享认证工具 — token 管理、认证请求、登录校验、退出
 * 所有页面通过 <script src="/static/js/auth.js"> 引入
 */
const Auth = {
  TOKEN_KEY: 'access_token',
  USER_KEY: 'user_info',

  getToken() {
    return localStorage.getItem(this.TOKEN_KEY);
  },

  setToken(token) {
    localStorage.setItem(this.TOKEN_KEY, token);
  },

  removeToken() {
    localStorage.removeItem(this.TOKEN_KEY);
  },

  getUser() {
    try {
      const raw = localStorage.getItem(this.USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },

  setUser(user) {
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
  },

  removeUser() {
    localStorage.removeItem(this.USER_KEY);
  },

  isLoggedIn() {
    return !!this.getToken();
  },

  /**
   * 带认证的 fetch 封装：自动附加 Authorization header，401 时清除状态并跳转登录
   */
  async authFetch(url, opts = {}) {
    const token = this.getToken();
    if (token) {
      opts.headers = opts.headers || {};
      opts.headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(url, opts);
    if (res.status === 401) {
      this.removeToken();
      this.removeUser();
      window.location.href = '/login';
      throw new Error('Unauthorized');
    }
    return res;
  },

  /**
   * 退出登录：调用 logout 接口清除 cookie，清除本地状态，跳转登录页
   */
  async logout() {
    try {
      await fetch('/api/auth/logout', { method: 'POST' });
    } catch { /* ignore */ }
    this.removeToken();
    this.removeUser();
    window.location.href = '/login';
  },

  /**
   * 页面加载时调用：未登录则跳转到 /login
   */
  requireAuth() {
    if (!this.isLoggedIn()) {
      window.location.href = '/login';
    }
  },

  /**
   * 初始化 header 用户信息（下拉菜单显示用户名/角色）
   */
  initHeader() {
    const user = this.getUser();
    if (!user) return;
    const nameEl = document.getElementById('dropdownUsername');
    if (nameEl) nameEl.textContent = user.real_name || user.username;
    const roleEl = document.getElementById('dropdownRole');
    if (roleEl) roleEl.textContent = user.role === 'admin' ? '管理员' : '操作员';
    const navUsers = document.getElementById('navUsers');
    if (navUsers && user.role === 'admin') navUsers.style.display = '';
  }
};
