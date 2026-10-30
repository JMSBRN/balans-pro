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
 *     Put the web app URL into FORM_ENDPOINT in script.js.
 *
 * Google Sheets log (optional): select setupSheet and press Run once. It creates the
 * «Заявки с сайта БалансПро» spreadsheet in your Drive and logs its link; every request is
 * then added as a row. After changing this code: Deploy → Manage deployments → edit →
 * Version: New version, so the web app URL stays the same.
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

const HEADERS = ['Дата и время', 'Форма', 'Имя', 'Телефон', 'E-mail', 'Сообщение', 'Страница', 'Статус'];

const STATUSES = ['Новая', 'В работе', 'Клиент', 'Отказ'];

function setupSheet() {
  const props = PropertiesService.getScriptProperties();
  if (props.getProperty('SHEET_ID')) {
    Logger.log(`Already set up: ${SpreadsheetApp.openById(props.getProperty('SHEET_ID')).getUrl()}`);
    return;
  }
  const book = SpreadsheetApp.create('Заявки с сайта БалансПро');
  book.setSpreadsheetTimeZone('Europe/Minsk');
  const sheet = book.getSheets()[0].setName('Заявки');
  sheet.appendRow(HEADERS);
  sheet.setFrozenRows(1);
  sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold').setBackground('#efe6fb');
  sheet.getRange('A:A').setNumberFormat('dd.mm.yyyy hh:mm');
  sheet.getRange('H2:H').setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(STATUSES).build());
  [140, 140, 160, 150, 200, 320, 260, 120].forEach((w, i) => sheet.setColumnWidth(i + 1, w));
  props.setProperty('SHEET_ID', book.getId());
  Logger.log(`Spreadsheet: ${book.getUrl()}`);
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

  const lead = {
    form: clean('form'), name, phone, email: clean('email'), message: clean('message'), page: clean('page'),
  };
  // Each channel on its own: a Sheets hiccup must not lose the Telegram message, and back
  let saved = false;
  try {
    saved = save_(lead);
  } catch (err) {
    console.error('Sheet: ' + err);
  }
  try {
    notify_(lead);
  } catch (err) {
    console.error('Telegram: ' + err);
    if (!saved) throw err;
  }
  return reply_('ok');
}

function save_(lead) {
  const id = PropertiesService.getScriptProperties().getProperty('SHEET_ID');
  if (!id) return false;
  // A leading = + - @ would make Sheets treat the text as a formula
  const text = (v) => (/^[=+\-@]/.test(v) ? `'${v}` : v);
  SpreadsheetApp.openById(id).getSheetByName('Заявки').appendRow([
    new Date(), lead.form, text(lead.name), text(lead.phone), text(lead.email), text(lead.message), lead.page, STATUSES[0],
  ]);
  return true;
}

function notify_({ form, name, phone, email, message, page }) {
  const lines = [
    '📩 <b>Новая заявка с сайта</b>' + (form ? ` — ${esc_(form)}` : ''),
    '',
    `<b>Имя:</b> ${esc_(name)}`,
    `<b>Телефон:</b> ${esc_(phone)}`,
  ];
  if (email) lines.push(`<b>E-mail:</b> ${esc_(email)}`);
  if (message) lines.push('', esc_(message));
  if (page) lines.push('', `<i>${esc_(page)}</i>`);
  send_(lines.join('\n'));
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
