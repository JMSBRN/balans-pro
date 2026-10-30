/**
 * Sends the site's request forms to Telegram. Runs as a Google Apps Script web app,
 * so the bot token stays in the script's properties instead of the public site code.
 *
 * Setup (once):
 *  1. In Telegram, create a bot with @BotFather (/newbot) and copy its token.
 *  2. Open the new bot and press Start (or send it any message).
 *  3. On script.google.com create a project, paste this file into Code.gs.
 *  4. Project Settings → Script properties → add TELEGRAM_TOKEN = the token.
 *  5. Select the setup function and press Run; allow access. The log shows the chat it found.
 *  6. Deploy → New deployment → Web app: Execute as «Me», Who has access «Anyone».
 *     Put the web app URL into data-endpoint of the forms in index.html.
 */

const MAX_PER_HOUR = 30; // a cap against form spam
const LIMITS = { name: 100, phone: 40, email: 120, message: 2000, form: 60, page: 300 };

function setup() {
  const props = PropertiesService.getScriptProperties();
  const token = props.getProperty('TELEGRAM_TOKEN');
  if (!token) throw new Error('Add the TELEGRAM_TOKEN script property first');
  const res = JSON.parse(UrlFetchApp.fetch(`https://api.telegram.org/bot${token}/getUpdates`).getContentText());
  const chats = (res.result || []).map((u) => (u.message || u.my_chat_member || {}).chat).filter(Boolean);
  if (!chats.length) throw new Error('No messages yet: open the bot in Telegram, press Start and run setup again');
  const chat = chats[chats.length - 1];
  props.setProperty('TELEGRAM_CHAT_ID', String(chat.id));
  send_(`✅ Заявки с сайта БалансПро будут приходить сюда.`);
  Logger.log(`Chat saved: ${chat.id} (${chat.first_name || chat.title || ''})`);
}

function doPost(e) {
  const p = (e && e.parameter) || {};
  // Bots fill the hidden field; people never see it
  if (p.website) return reply_('ok');
  const clean = (key) => String(p[key] || '').trim().slice(0, LIMITS[key]);
  const name = clean('name');
  const phone = clean('phone');
  if (!name || phone.replace(/\D/g, '').length < 9) return reply_('invalid');

  const cache = CacheService.getScriptCache();
  const count = Number(cache.get('count') || 0);
  if (count >= MAX_PER_HOUR) return reply_('busy');
  cache.put('count', String(count + 1), 3600);

  const lines = [
    '📩 <b>Новая заявка с сайта</b>' + (clean('form') ? ` — ${esc_(clean('form'))}` : ''),
    '',
    `<b>Имя:</b> ${esc_(name)}`,
    `<b>Телефон:</b> ${esc_(phone)}`,
  ];
  if (clean('email')) lines.push(`<b>E-mail:</b> ${esc_(clean('email'))}`);
  if (clean('message')) lines.push('', esc_(clean('message')));
  if (clean('page')) lines.push('', `<i>${esc_(clean('page'))}</i>`);
  send_(lines.join('\n'));
  return reply_('ok');
}

function send_(text) {
  const props = PropertiesService.getScriptProperties();
  UrlFetchApp.fetch(`https://api.telegram.org/bot${props.getProperty('TELEGRAM_TOKEN')}/sendMessage`, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify({
      chat_id: props.getProperty('TELEGRAM_CHAT_ID'),
      text,
      parse_mode: 'HTML',
      disable_web_page_preview: true,
    }),
  });
}

function esc_(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function reply_(status) {
  return ContentService.createTextOutput(JSON.stringify({ status })).setMimeType(ContentService.MimeType.JSON);
}
