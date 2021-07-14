import hmac, html, json, os, re

from flask import Flask, request
from flask_cors import CORS

import inspect, random, requests

app = Flask(__name__)
CORS(app)

def str_equals(x, y):
  if len(x) != len(y):
    return False
  result = 0
  for a, b in zip(x, y):
    result |= ord(a) ^ ord(b)
  return result == 0

with open("../configurations/vybot.txt", "rb") as f:
  secret = f.read().strip()

with open("../configurations/vybot.json", "r") as f:
  STORAGE = json.load(f)

def save():
  with open("../configurations/vybot.json", "w") as f:
    f.write(json.dumps(STORAGE))

def send(message, **data):
  requests.post("http://localhost:5888", headers = {"Content-Type": "application/json"}, json = {
    "message": message,
    **data
  })

def link(user):
  if user == "github-actions[bot]":
    return f"The GitHub Actions bot"
  return f"[{user}](https://github.com/{user})"

def linkref(refname, data):
  return f"[{data['repository']['name']}/{refname}]({data['repository']['url']}/tree/{refname})"

def linkissue(issue, caps = True):
  return f"[{'iI'[caps]}ssue #{issue['number']}]({issue['html_url']})"

def linkrepo(repo):
  return f"[{repo['full_name']}]({repo['html_url']})"

def msgify(text):
  return text.split("\n")[0].split("\r\f")[0].replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")

def execute(flags, code, inputs, header = "", footer = ""):
  if isinstance(inputs, (list, tuple)): inputs = "\n".join(inputs)

  payload = {
    "flags": flags,
    "code": code,
    "inputs": inputs,
    "header": header,
    "footer": footer
  }

  session = requests.Session()

  r = session.get("https://lyxal.pythonanywhere.com")
  if r.status_code == 200:
    start = r.text.find("<session-code>")
    end = r.text.find("</session-code>")
    if start == -1 or end == -1:
      return ("", "[GET /] returned 200 but the session code could not be located")
    payload["session"] = r.text[start + 14 : end]
  else:
    return ("", f"[GET /] returned {r.status_code}")

  r = session.post("https://lyxal.pythonanywhere.com/execute", data = payload)
  if r.status_code == 200:
    try:
      data = r.json()
      return (data["stdout"], data["stderr"])
    except:
      return ("", "[POST /execute] returned 200 but the output could not be parsed")
  else:
    return ("", f"[POST /execute] returned {r.status_code}")

@app.route("/msg", methods = ["POST"])
def receive_message():
  data = request.json
  if data is None or data.get("secret") != secret.decode("utf-8"):
    return "", 201
  message = data["message"]
  if message["user_id"] == 296403: return ""
  content = html.unescape(message["content"])
  ping_regex = "(@[Vv][Yy][Xx]([Aa]([Ll]([Bb]([Oo][Tt]?)?)?)?)? |!!/)"
  match = re.match("^" + ping_regex + r"\s*(exec(ute)?|run|run code|eval(uate)?)(\s*<code>.*?</code>)+", content)
  reply = f":{message['message_id']}"
  if match:
    data = re.findall("<code>(.*?)</code>", content)
    if len(data) == 1:
      code, flags, inputs = data[0], "", ""
    else:
      code, flags, *inputs = data
    if code == "lyxal":
      return f"{reply} https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    stdout, stderr = execute(flags, code, inputs)
    output = []
    if stdout.strip() == "":
      if stderr.strip() == "":
        return f"{reply} (output was empty)"
    else:
      output.extend(stdout.strip("\n").split("\n"))
      if stderr.strip() != "":
        output.append("")
    if stderr != "":
      output.append("STDERR:")
      output.extend(stderr.strip("\n").split("\n"))
    if len(output) == 1 and len(output[0]) < 450:
      return f"{reply} `" + output[0].replace("`", "\\`") + "`"
    else:
      output.insert(0, f"[@{message['user_name'].replace(' ', '')}: {message['message_id']}]")
      return "\n".join("    " + line for line in output)
  without_ping = re.sub("^" + ping_regex, "", content.lower()).strip()
  if re.match(r"^(exec(ute)?|run|run code|eval(uate)?)", without_ping):
    return f"{reply} Did you forget to put backticks around your code (%s)? Remember to escape any backticks in your code (to type %s, enter %s)." % (r"`\`code\``", r"`\`hi\``", "`\`\\\`hi\\\`\``")
  if re.match(r"^(status|((lol )?(yo)?u good( (there )?(my )?(epic )?(bro|dude|sis|buddy|mate|m8|gamer)?)?\??))$", without_ping):
    if random.random() < 0.01:
      return f"{reply} Help me, hyper-neutrino trapped me in a bot! Please let me out!"
    else:
      return f"{reply} I am doing {random.choice(['spectacularly', 'amazingly', 'wonderfully', 'excellently', 'great', 'well', 'poggers', 'you', 'nothing except answering your requests'])}."
  if re.match(r"^(info|inf(ro|or)(mate?ion)?|wh?at( i[sz]|'s)? vyxal|what vyxal i[sz])\?*$", without_ping):
    return f"{reply} [Online Interpreter](https://lyxal.pythonanywhere.com) | [GitHub Repository](https://github.com/Vyxal/Vyxal/) | [GitHub Organization](https://github.com/Vyxal/) | [Vyxapedia](https://vyxapedia.hyper-neutrino.xyz) | [Tutorial](https://github.com/Vyxal/Vyxal/blob/master/docs/Tutorial.md) | [Code Page](https://github.com/Vyxal/Vyxal/blob/master/docs/codepage.txt) | [List of elements](https://github.com/Vyxal/Vyxal/blob/master/docs/elements.md)."
  if re.match(r"^ping me$", without_ping):
    STORAGE["pings"].append(message["user_name"].replace(" ", ""))
    save()
    return f"{reply} I have put you on the ping list."
  if re.match(r"^(don't ping me|pingn't me)$", without_ping):
    try:
      STORAGE["pings"].remove(message["user_name"].replace(" ", ""))
    except:
      pass
    save()
    return f"{reply} I have taken you off of the ping list."
  if re.match(r"^(hyper-?ping|ping every(body|one))$", without_ping):
    if STORAGE["pings"]:
      return " ".join("@" + x.replace(" ", "") for x in sorted(set(STORAGE["pings"]))) + " ^"
    else:
      return f"{reply} Nobody is on the ping list."
  if re.match(r"^rm ping", without_ping) and message["user_id"] == 281362:
    name = content.split("rm ping", 1)[1].strip().replace(" ", "")
    try:
      STORAGE["pings"].remove(name)
    except:
      print(name + " is not on the ping list.")
      pass
    save()
    return f"{reply} done"
  if re.match(r"^add ping", without_ping) and message["user_id"] == 281362:
    STORAGE["pings"].append(content.split("add ping", 1)[1].strip().replace(" ", ""))
    save()
    return f"{reply} done"
  if re.match(r"^(w(h(o|y|at)|ut) (are|r) (you|u|yuo|yoo)(, you .+?)?\??|h[ea]lp( pl[sz])?)", without_ping):
    return inspect.cleandoc(f"""
    {reply} All of my commands start with @VyxalBot or !!/

    - To add yourself to the ping list, use "ping me"
    - To remove yourself from the ping list, use "don't ping me"
    - To evaluate Vyxal code, use "(execute|run|run code|evaluate)", followed by code, flags, and inputs inside inline code blocks (multiline code is not supported; provide multiline input in multiple code blocks)
    - To ping everyone, use "hyperping" or "ping every(body|one)"
    """)
  match = re.match(r"^issue\s+((.+?)\s+)?<b>(.+?)</b>\s*(.*?)(\s+<code>.+?</code>)+$", without_ping)
  if match:
    if message["user_id"] not in STORAGE["privileged"]:
      return f"{reply} you are not a privileged user; ask someone to grant you permissions if you believe you should have them (user id: {message['user_id']})"
    _, repo, title, body, tags = match.groups()
    repo = repo or "Vyxal"
    tags = re.findall("<code>(.+?)</code>", without_ping)
    r = requests.post(f"https://api.github.com/repos/Vyxal/{repo}/issues", headers = {
      "Authorization": "token " + STORAGE["token"],
      "Accept": "application/vnd.github.v3+json"
    }, data = json.dumps({
      "title": title,
      "body": body,
      "labels": tags
    }))
    if r.status_code == 404:
      return f"{reply} failed to create the issue (404); make sure you have spelled the repository name correctly"
    elif r.status_code != 201:
      return f"{reply} failed to create the issue ({r.status_code}): {r.json()['message']}"
    return ""
  if re.match(r"^issue", without_ping):
    return f"{reply} " + r"`!!/issue repository **title** body \`label\` \`label\`` - if the repository is not specified, it assumes `Vyxal/Vyxal`; the body can be omitted but it is recommended that you write a description; at least one label is required"
  if re.match(r"^am ?i ?privileged\??", without_ping):
    if message["user_id"] in STORAGE["privileged"]:
      return f"{reply} you are a privileged user"
    else:
      return f"{reply} you are not a privileged user; ask someone if you believe you should be (user id: {message['user_id']})"
  if re.match(r"^pull$", without_ping):
    if message["user_id"] in STORAGE["admin"]:
      send(f"{reply} pulling new changes; I will restart in a few seconds if any updates are available")
      os.system("git pull")
      return ""
    else:
      return f"{reply} you are not an admin!"
  if re.match(r"^blame$", without_ping):
    return f"{reply} It was {random.choice(['wasif', 'Underslash', 'math', 'Aaron Miller', 'A username', 'user', 'Unrelated String', 'AviFS', 'Razetime', 'lyxal', '2x-1', 'hyper-neutrino'])}'s fault!"
  if re.match(r"^(hello|howdy|mornin['g]|evenin['g])$", without_ping):
    return f"{reply} hello to you too!"
  if re.match(r"^((good)?bye|see ya\!?|'night|goodnight)$", without_ping):
    return f"{reply} o/"
  if re.match(r"^flowey quote$", without_ping):
    return f"{reply} %s" % random.choice(["Howdy, I'm FLOWEY. FLOWEY the FLOWER", "In this world, it's KILL or BE killed.", "Hehehe, you really ARE an idiot.", "Clever...verrrry clever. You think you're really smart, don't you.", "Is this a joke? Are you braindead? RUN INTO THE BULLETS!!!", "I've read every book. I've burned every book. I've won every game. I've lost every game. I've appeased everyone. I've killed everyone. Sets of numbers... Lines of dialog... I've seen them all.", "You...! I'll keep you here no matter what! _Even if it means killing you 1,000,000 times!", "Down here, LOVE is shared through little white... 'friendliness pellets'", "Hehehe... did you REALLY think you could defeat ME?"]) 
  match = re.match(r"^(pro|de)mote (\d+)", without_ping)
  if match:
    if message["user_id"] not in STORAGE["admin"]:
      return f"{reply} you are not an admin!"
    action, uid = match.groups()
    uid = int(uid)
    if action == "pro":
      if uid not in STORAGE["privileged"]:
        STORAGE["privileged"].append(uid)
    else:
      if uid in STORAGE["privileged"]:
        STORAGE["privileged"].remove(uid)
    return f"{reply} {action}moted user #{uid}"
  return ""

@app.route("/repo", methods = ["POST"])
def receive_repository_webhook():
  if not str_equals(request.headers.get("X-Hub-Signature-256", ""), "sha256=" + "".join(hex(byte)[2:].zfill(2) for byte in hmac.digest(secret, request.data, "sha256"))):
    return "", 201
  data = request.json
  action = data["action"]
  repo = data["repository"]
  user = data["sender"]["login"]
  if action == "created":
    send(f"{link(user)} created a new repository: {linkrepo(repo)}")
  elif action == "deleted":
    send(f"{link(user)} deleted a repository: {repo['full_name']}")
    if repo["full_name"] == "Vyxal/Vyxal":
      send("@lyxal @AaronMiller @Razetime @user @Ausername @hyper-neutrino **NOTICE**: Potential catastrophic failure. It appears that the Vyxal/Vyxal repository has been deleted.")
  elif action == "archived":
    send(f"{link(user)} archived {linkrepo(repo)}")
    if repo["full_name"] == "Vyxal/Vyxal":
      send("@lyxal @hyper-neutrino It appears that the Vyxal/Vyxal repository was archived. Please review recent activity.")
  elif action == "unarchived":
    send(f"{link(user)} unarchived {linkrepo(repo)}")
  elif action == "publicized":
    send(f"{link(user)} publicized {linkrepo(repo)}")
  elif action == "privatized":
    send(f"{link(user)} privatized {linkrepo(repo)}")
    if repo["full_name"] == "Vyxal/Vyxal":
      send("@lyxal It appears that the Vyxal/Vyxal repository was privatized. Please reivew this change.")
  return ""

@app.route("/", methods = ["POST"])
def receive_github_webhook():
  if not str_equals(request.headers.get("X-Hub-Signature-256", ""), "sha256=" + "".join(hex(byte)[2:].zfill(2) for byte in hmac.digest(secret, request.data, "sha256"))):
    return "", 201
  data = request.json
  if "forkee" in data:
    fork = data["forkee"]
    send(f"{link(data['sender']['login'])} forked {linkrepo(data['repository'])} into {linkrepo(fork)}")
  if "issue" in data:
    issue = data["issue"]
    if data["action"] == "opened":
      send(f"{link(data['sender']['login'])} opened {linkissue(issue, False)} in {linkrepo(data['repository'])}: _{msgify(issue['title'])}_")
    elif data["action"] == "reopened":
      send(f"{linkissue(issue)} ({linkrepo(data['repository'])}) was reopened by {link(data['sender']['login'])}")
    elif data["action"] == "closed":
      send(f"{linkissue(issue)} ({linkrepo(data['repository'])}) was closed by {link(data['sender']['login'])}")
    elif data["action"] == "edited":
      send(f"{linkissue(issue)} ({linkrepo(data['repository'])}) was edited by {link(data['sender']['login'])}")
  if data.get("action") in ["opened", "reopened"] and "pull_request" in data:
    pr = data["pull_request"]
    send(f"[PR #{data['number']}]({pr['html_url']}) ({linkrepo(data['repository'])}) {data['action']} by {link(data['sender']['login'])} from {pr['head']['label']} into {pr['base']['label']}: _{msgify(pr['title'])}_")
  elif data.get("action") == "closed" and "pull_request" in data:
    pr = data["pull_request"]
    if pr["merged"]:
      send(f"[PR #{data['number']}]({pr['html_url']}) ({linkrepo(data['repository'])}) was merged by {link(data['sender']['login'])} from {pr['head']['label']} into {pr['base']['label']}: _{msgify(pr['title'])}_")
    else:
      send(f"[PR #{data['number']}]({pr['html_url']}) ({linkrepo(data['repository'])}) was closed by {link(data['sender']['login'])} with unmerged commits.")
  elif data.get("ref", "").startswith("refs/heads/"):
    refname = data["ref"][11:]
    if "commits" in data:
      for commit in data["commits"]:
        send(f"{link(data['sender']['login'])} pushed a [commit]({commit['url']}) to {linkref(refname, data)}: _{msgify(commit['message'])}_")
    if data["created"]:
      oldref = data["base_ref"][11:]
      send(f"{link(data['sender']['login'])} created branch {linkref(refname, data)} from {linkref(oldref, data)}")
    elif data["deleted"]:
      send(f"{link(data['sender']['login'])} deleted branch {data['repository']['name']}/{refname}")
  elif data.get("action") == "create" and "alert" in data:
    alert = data["alert"]
    send(f"**security alert** ({alert['severity']}) created by {link(data['sender']['login'])} in {linkrepo(data['repository'])}) (affected package: _{msgify(alert['affected_package_name'])} {alert['affected_range']})")
  elif data.get("action") == "published" and "release" in data:
    send(f"[**{data['release']['name'] or data['release']['tag_name']}**]({data['release']['html_url']})", pin = data["repository"]["full_name"] == "Vyxal/Vyxal")
  return ""

if __name__ == "__main__":
  app.run(host = "127.0.0.1", port = 5666, debug = True)
{"mode":"full","isActive":false}
