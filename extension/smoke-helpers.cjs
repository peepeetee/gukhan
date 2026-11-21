// SPDX-License-Identifier: Apache-2.0
// Shared by the browser smoke tests. The shipped manifest asks for no site at install; the browser's
// permission bubble cannot be pressed by automation. A test copy therefore declares the HTTP(S) hosts as
// already granted. The code under test is unchanged: permissions.contains and permissions.request answer
// yes at once, and registering and injecting the content script are the real thing.
const fs = require('node:fs');
const path = require('node:path');

function copyWithHosts(src, dest) {
  fs.rmSync(dest, {recursive: true, force: true});
  fs.cpSync(src, dest, {recursive: true});
  grantHosts(dest);
  return dest;
}
function grantHosts(dir) {
  const file = path.join(dir, 'manifest.json');
  const manifest = JSON.parse(fs.readFileSync(file, 'utf8'));
  manifest.host_permissions = ['http://*/*', 'https://*/*'];
  fs.writeFileSync(file, JSON.stringify(manifest, null, 2));
}
// Run in an extension page (settings): what the popup does after the reader allows a host.
const siteMessage = (host, on) => `(async () => {
  const [tab] = await chrome.tabs.query({url: 'http://${host}/*'});
  return chrome.runtime.sendMessage({type: 'site', host: '${host}', on: ${on}, tabId: tab && tab.id});
})()`;
module.exports = {copyWithHosts, grantHosts, siteMessage};
