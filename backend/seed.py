from .models import ProjectFile, FileStatus

INODE_LEGACY = """#include "fs.h"\n#include "buf.h"\n\n#define NDIRECT 12\n#define NINDIRECT (BSIZE / sizeof(uint))\n\nuint\nbmap_resolve(struct inode *ip, uint bn)\n{\n    uint addr, *a;\n    struct buf *bp;\n\n    if (bn < NDIRECT) {\n        if ((addr = ip->addrs[bn]) == 0)\n            ip->addrs[bn] = addr = balloc(ip->dev);\n        return addr;\n    }\n    bn -= NDIRECT;\n\n    if (bn < NINDIRECT) {\n        if ((addr = ip->addrs[NDIRECT]) == 0)\n            ip->addrs[NDIRECT] = addr = balloc(ip->dev);\n        bp = bread(ip->dev, addr);\n        a = (uint*)bp->data;\n        if ((addr = a[bn]) == 0) {\n            a[bn] = addr = balloc(ip->dev);\n            log_write(bp);\n        }\n        brelse(bp);\n        return addr;\n    }\n\n    panic("bmap_resolve: out of range");\n}\n"""
INODE_AI = """#include "fs.h"\n#include "buf.h"\n\n#define NDIRECT 11\n#define NINDIRECT (BSIZE / sizeof(uint))\n#define NDINDIRECT (NINDIRECT * NINDIRECT)\n\nuint\nbmap_resolve(struct inode *ip, uint bn)\n{\n    uint addr, *a;\n    struct buf *bp, *bp2;\n\n    if (bn < NDIRECT) {\n        if ((addr = ip->addrs[bn]) == 0)\n            ip->addrs[bn] = addr = balloc(ip->dev);\n        return addr;\n    }\n    bn -= NDIRECT;\n\n    if (bn < NINDIRECT) {\n        if ((addr = ip->addrs[NDIRECT]) == 0)\n            ip->addrs[NDIRECT] = addr = balloc(ip->dev);\n        bp = bread(ip->dev, addr);\n        a = (uint*)bp->data;\n        if ((addr = a[bn]) == 0) {\n            a[bn] = addr = balloc(ip->dev);\n            log_write(bp);\n        }\n        brelse(bp);\n        return addr;\n    }\n    bn -= NINDIRECT;\n\n    if (bn < NDINDIRECT) {\n        if ((addr = ip->addrs[NDIRECT + 1]) == 0)\n            ip->addrs[NDIRECT + 1] = addr = balloc(ip->dev);\n        bp = bread(ip->dev, addr);\n        a = (uint*)bp->data;\n\n        int outer = bn / NINDIRECT;\n        if ((addr = a[outer]) == 0) {\n            a[outer] = addr = balloc(ip->dev);\n            log_write(bp);\n        }\n        brelse(bp);\n\n        bp2 = bread(ip->dev, addr);\n        a = (uint*)bp2->data;\n\n        int inner = bn - outer;\n        if ((addr = a[inner]) == 0) {\n            a[inner] = addr = balloc(ip->dev);\n            log_write(bp2);\n        }\n        brelse(bp2);\n        return addr;\n    }\n\n    panic("bmap_resolve: out of range");\n}\n"""
INODE_TRACEBACK = '''Running sandbox test suite: test_bmap_large_file...\nallocating 70000 logical blocks to exercise doubly-indirect path\nASSERT FAILED at fs/inode_alloc.c:75 in bmap_resolve() -- index 69884 out of bounds for indirect block (expected 0-255)\ntest_bmap_large_file: FAILED (1/4 cases passed)\n'''

PERM_CHECK_LEGACY = """#include "fs.h"\n\nint\nperm_check_write(struct inode *ip, int uid)\n{\n    if (ip->uid != uid)\n        return 0;\n    return (ip->mode & S_IWUSR) != 0;\n}\n"""

SENTIMENT_LEGACY = """import csv\n\nPOSITIVE_WORDS = {"growth", "profit", "improved", "strong", "exceeded"}\nNEGATIVE_WORDS = {"loss", "decline", "weak", "litigation", "restated"}\n\ndef load_lexicon_counts(report_text):\n    tokens = report_text.lower().split()\n    pos = sum(1 for t in tokens if t in POSITIVE_WORDS)\n    neg = sum(1 for t in tokens if t in NEGATIVE_WORDS)\n    return {"positive": pos, "negative": neg}\n\ndef sentiment_score(report_text):\n    counts = load_lexicon_counts(report_text)\n    total = counts["positive"] + counts["negative"]\n    if total == 0:\n        return 0.0\n    return (counts["positive"] - counts["negative"]) / total\n\ndef score_filing_batch(filing_paths):\n    rows = []\n    for path in filing_paths:\n        with open(path) as fh:\n            text = fh.read()\n        rows.append({"path": path, "lm_score": sentiment_score(text)})\n    return rows\n\ndef export_csv(rows, out_path):\n    with open(out_path, "wb") as fh:\n        writer = csv.DictWriter(fh, fieldnames=["path", "lm_score"])\n        writer.writeheader()\n        writer.writerows(rows)\n"""
SENTIMENT_AI = """import csv\nfrom dataclasses import dataclass\n\nPOSITIVE_WORDS = {"growth", "profit", "improved", "strong", "exceeded"}\nNEGATIVE_WORDS = {"loss", "decline", "weak", "litigation", "restated"}\n\n@dataclass\nclass TRVResult:\n    path: str\n    lm_score: float\n    trv_score: float\n    confidence: float\n\nclass SentimentModel:\n    def __init__(self, model_name="phobert-finetuned-trv-v1"):\n        self.model_name = model_name\n\n    def predict(self, text: str) -> tuple[float, float]:\n        tokens = text.lower().split()\n        pos = sum(1 for t in tokens if t in POSITIVE_WORDS)\n        neg = sum(1 for t in tokens if t in NEGATIVE_WORDS)\n        total = max(pos + neg, 1)\n        trv = (pos - neg) / total\n        confidence = min(1.0, total / 10)\n        return trv, confidence\n\n_MODEL = SentimentModel()\n\ndef lexicon_score(report_text: str) -> float:\n    tokens = report_text.lower().split()\n    pos = sum(1 for t in tokens if t in POSITIVE_WORDS)\n    neg = sum(1 for t in tokens if t in NEGATIVE_WORDS)\n    total = pos + neg\n    return 0.0 if total == 0 else (pos - neg) / total\n\ndef score_filing_batch(filing_paths: list[str]) -> list[TRVResult]:\n    results = []\n    for path in filing_paths:\n        with open(path, encoding="utf-8") as fh:\n            text = fh.read()\n        trv, confidence = _MODEL.predict(text)\n        results.append(TRVResult(path=path, lm_score=lexicon_score(text), trv_score=trv, confidence=confidence))\n    return results\n\ndef export_csv(rows: list[TRVResult], out_path: str) -> None:\n    with open(out_path, "w", newline="", encoding="utf-8") as fh:\n        writer = csv.DictWriter(fh, fieldnames=["path", "lm_score", "trv_score", "confidence"])\n        writer.writeheader()\n        for r in rows:\n            writer.writerow({"path": r.path, "lm_score": r.lm_score, "trv_score": r.trv_score, "confidence": r.confidence})\n"""

AUTH_LEGACY = """import urllib\nimport httplib\n\nclass AuthController:\n    def __init__(self, session_store):\n        self.session_store = session_store\n        self.attempts = {}\n\n    def foo(self):\n        x = bar()\n        return x[0]\n\n    def login(self, username, password):\n        if username in self.attempts and self.attempts[username] > 3:\n            raise Exception("Too many attempts")\n        token = self._hash(username, password)\n        conn = httplib.HTTPConnection("auth.internal")\n        conn.request("POST", "/verify", urllib.urlencode({"token": token}))\n        resp = conn.getresponse()\n        return resp.status == 200\n\n    def _hash(self, username, password):\n        import md5\n        m = md5.new()\n        m.update(username + password)\n        return m.hexdigest()\n\n    def logout(self, username):\n        print "Logging out", username\n        self.session_store.pop(username, None)\n"""
AUTH_AI = """import urllib.request\nimport http.client\n\nclass AuthController:\n    def __init__(self, session_store):\n        self.session_store = session_store\n        self.attempts = {}\n\n    async def foo(self):\n        x = await bar()\n        return x[0]\n\n    def login(self, username, password):\n        if username in self.attempts and self.attempts[username] > 3:\n            raise Exception("Too many attempts")\n        token = self._hash(username, password)\n        conn = http.client.HTTPConnection("auth.internal")\n        conn.request("POST", "/verify", urllib.parse.urlencode({"token": token}))\n        resp = conn.getresponse()\n        return resp.status == 200\n\n    def _hash(self, username, password):\n        import hashlib\n        m = hashlib.md5()\n        m.update((username + password).encode())\n        return m.hexdigest()\n\n    def logout(self, username):\n        print("Logging out", username)\n        self.session_store.pop(username, None)\n"""
AUTH_TRACEBACK = '''Traceback (most recent call last):\n  File "/sandbox/runner.py", line 88, in run_module\n    result = module.foo()\n  File "/sandbox/controllers/AuthController.py", line 10, in foo\n    x = await bar()\nTypeError: object NoneType can't be used in 'await' expression\n'''

USER_LEGACY = """import StringIO\n\nclass UserController:\n    def __init__(self, db):\n        self.db = db\n\n    def export_csv(self, user_ids):\n        buf = StringIO.StringIO()\n        for uid in user_ids:\n            record = self.db.fetch(uid)\n            buf.write("%s,%s\\n" % (record['id'], record['name']))\n        return buf.getvalue()\n\n    def bulk_update(self, updates):\n        for uid, fields in updates.iteritems():\n            self.db.update(uid, fields)\n"""
USER_AI = """import io\n\nclass UserController:\n    def __init__(self, db):\n        self.db = db\n\n    def export_csv(self, user_ids):\n        buf = io.StringIO()\n        for uid in user_ids:\n            record = self.db.fetch(uid)\n            buf.write("%s,%s\\n" % (record['id'], record['name']))\n        return buf.getvalue()\n\n    def bulk_update(self, updates):\n        for uid, fields in updates.items():\n            self.db.update(uid, fields)\n"""
USER_TRACEBACK = '''Traceback (most recent call last):\n  File "/sandbox/runner.py", line 41, in run_module\n    controller.bulk_update(sample_updates)\n  File "/usr/lib/python3.10/concurrent/futures/thread.py", line 58, in run\n    result = self.fn(*self.args, **self.kwargs)\n  File "/usr/lib/python3.10/concurrent/futures/_base.py", line 387, in result\n    return self.__get_result()\n  File "/sandbox/controllers/UserController.py", line 16, in bulk_update\n    self.db.update(uid, fields)\n  File "/sandbox/mocks/db_mock.py", line 22, in update\n    raise KeyError(uid)\nKeyError: 'u_204'\n'''

CUSTOMER_LEGACY = """class Customer(object):\n    def __init__(self, name, email):\n        self.name = name\n        self.email = email\n        self._orders = []\n\n    def add_order(self, order):\n        self._orders.append(order)\n        return len(self._orders)\n\n    def total_spent(self):\n        return sum(o.amount for o in self._orders)\n\n    def __repr__(self):\n        return "Customer(%r, %r)" % (self.name, self.email)\n"""
CUSTOMER_AI = """class Customer:\n    def __init__(self, name, email):\n        self.name = name\n        self.email = email\n        self._orders = []\n\n    def add_order(self, order):\n        self._orders.append(order)\n        return len(self._orders)\n\n    def total_spent(self):\n        return sum(o.amount for o in self._orders)\n\n    def __repr__(self):\n        return f"Customer({self.name!r}, {self.email!r})"\n"""

ORDER_LEGACY = """class Order:\n    def __init__(self, items):\n        self.items = items\n\n    def amount(self):\n        total = 0\n        for item in self.items:\n            total += item['price'] * item['qty']\n        return total\n"""
ORDER_AI = """class Order:\n    def __init__(self, items):\n        self.items = items\n\n    def amount(self):\n        total = 0\n        for item in self.items:\n            total += item["price"] * item["qty"]\n        return total\n"""

DASH_LEGACY = """class Dashboard:\n    def render(self, widgets):\n        out = []\n        for w in widgets:\n            out.append("<div>%s</div>" % w.title)\n        return "\\n".join(out)\n"""
DASH_AI = """class Dashboard:\n    def render(self, widgets):\n        out = []\n        for w in widgets:\n            out.append(f"<div>{w.title}</div>")\n        return "\\n".join(out)\n"""

SIDEBAR_LEGACY = """class Sidebar:\n    def __init__(self, items):\n        self.items = items\n\n    def render(self):\n        return [unicode(i) for i in self.items]\n"""
SIDEBAR_AI = """class Sidebar:\n    def __init__(self, items):\n        self.items = items\n\n    def render(self):\n        return [str(i) for i in self.items]\n"""

HEADER_LEGACY = """class Header:\n    def __init__(self, title):\n        self.title = title\n"""
HEADER_AI = HEADER_LEGACY 

REPORT_R_LEGACY = """summarize_sales <- function(df) {\n  total <- sum(df$amount)\n  by_region <- tapply(df$amount, df$region, sum)\n  list(total = total, by_region = by_region)\n}\n\nprint_report <- function(df) {\n  result <- summarize_sales(df)\n  cat("Total sales:", result$total, "\\n")\n  print(result$by_region)\n}\n"""
REPORT_R_AI = """summarize_sales <- function(df) {\n  total <- sum(df$amount)\n  by_region <- tapply(df$amount, df$region, sum)\n  list(total = total, by_region = by_region)\n}\n\nprint_report <- function(df) {\n  result <- summarise_sales(df)\n  cat("Total sales:", result$total, "\\n")\n  print(result$by_region)\n}\n"""
REPORT_R_TRACEBACK = '''4: source(file = "analytics/report.R") at runner.R#3\n3: withVisible(eval(ei, envir)) at report.R#8\n2: eval(ei, envir) at report.R#8\n1: print_report(sales_df) at report.R#8\nError in print_report(sales_df) : could not find function "summarise_sales"\n'''

def _build_large_helpers_pair():
    legacy_lines, ai_lines = [], []
    for i in range(1, 201):
        legacy_lines.extend([f"def helper_{i}(x):", f"    return x + {i}"])
        ai_lines.extend([f"def helper_{i}(x):", f"    return x + {i}"])
    insert_at = 204
    legacy_lines[insert_at:insert_at] = ["def process_batch(records):", "    results = []", "    for r in records:", "        results.append(r.iteritems())", "    return results"]
    ai_lines[insert_at:insert_at] = ["def process_batch(records):", "    results = []", "    for r in records:", "        results.append(r.items())", "    return results"]
    return "\n".join(legacy_lines), "\n".join(ai_lines)

BATCH_HELPERS_LEGACY, BATCH_HELPERS_AI = _build_large_helpers_pair()
BATCH_HELPERS_TRACEBACK = '''Traceback (most recent call last):\n  File "/sandbox/runner.py", line 12, in run_module\n    out = module.process_batch(sample_records)\n  File "/sandbox/utils/BatchHelpers.py", line 208, in process_batch\n    results.append(r.items())\nAttributeError: 'list' object has no attribute 'items'\n'''

def build_seed_files() -> list[ProjectFile]:
    return [
        ProjectFile(file_id="f_inode", path="fs/inode_alloc.c", legacy_source=INODE_LEGACY, language="c", 
                    status=FileStatus.QUEUED, ai_source="", raw_traceback="",
                    target_ai_source=INODE_AI, target_traceback=INODE_TRACEBACK, target_status=FileStatus.FAILED,
                    persona="systems_engineer", use_case="U001 → U003 (A1: execution failure)"),
                    
        ProjectFile(file_id="f_xv6_perm", path="fs/perm_check.c", legacy_source=PERM_CHECK_LEGACY, language="c",
                    status=FileStatus.QUEUED, ai_source="", raw_traceback="",
                    target_ai_source="int perm_check_write(struct inode *ip, int uid) { return 1; }", target_status=FileStatus.PASSED,
                    persona="systems_engineer", use_case="U001"),
                    
        ProjectFile(file_id="f_sentiment", path="analytics/sentiment_model.py", legacy_source=SENTIMENT_LEGACY, language="python",
                    status=FileStatus.QUEUED, ai_source="", raw_traceback="",
                    target_ai_source=SENTIMENT_AI, target_status=FileStatus.PASSED,
                    persona="data_scientist", use_case="U002 → U004"),
                    
        ProjectFile(file_id="f_report_r", path="analytics/report.R", legacy_source=REPORT_R_LEGACY, language="r",
                    status=FileStatus.QUEUED, ai_source="", raw_traceback="",
                    target_ai_source=REPORT_R_AI, target_traceback=REPORT_R_TRACEBACK, target_status=FileStatus.FAILED,
                    persona="data_scientist", use_case="U002 → U003"),
                    
        ProjectFile(file_id="f_auth", path="controllers/AuthController.py", legacy_source=AUTH_LEGACY, language="python",
                    status=FileStatus.QUEUED, ai_source="", raw_traceback="",
                    target_ai_source=AUTH_AI, target_traceback=AUTH_TRACEBACK, target_status=FileStatus.FAILED),
                    
        ProjectFile(file_id="f_user", path="controllers/UserController.py", legacy_source=USER_LEGACY, language="python",
                    status=FileStatus.QUEUED, ai_source="", raw_traceback="",
                    target_ai_source=USER_AI, target_traceback=USER_TRACEBACK, target_status=FileStatus.FAILED),
                    
        ProjectFile(file_id="f_customer", path="models/Customer.py", legacy_source=CUSTOMER_LEGACY, language="python",
                    status=FileStatus.QUEUED, ai_source="", raw_traceback="",
                    target_ai_source=CUSTOMER_AI, target_status=FileStatus.PASSED),
                    
        ProjectFile(file_id="f_order", path="models/Order.py", legacy_source=ORDER_LEGACY, language="python",
                    status=FileStatus.QUEUED, ai_source="", raw_traceback="",
                    target_ai_source=ORDER_AI, target_status=FileStatus.PASSED),
                    
        ProjectFile(file_id="f_dashboard", path="views/Dashboard.py", legacy_source=DASH_LEGACY, language="python",
                    status=FileStatus.QUEUED, ai_source="", raw_traceback="",
                    target_ai_source=DASH_AI, target_status=FileStatus.PASSED),
                    
        ProjectFile(file_id="f_sidebar_view", path="views/Sidebar.py", legacy_source=SIDEBAR_LEGACY, language="python",
                    status=FileStatus.QUEUED, ai_source="", raw_traceback="",
                    target_ai_source=SIDEBAR_AI, target_status=FileStatus.PASSED),
                    
        ProjectFile(file_id="f_header", path="views/Header.py", legacy_source=HEADER_LEGACY, language="python",
                    status=FileStatus.QUEUED, ai_source="", raw_traceback="",
                    target_ai_source=HEADER_AI, target_status=FileStatus.PASSED),
                    
        ProjectFile(file_id="f_batch_helpers", path="utils/BatchHelpers.py", legacy_source=BATCH_HELPERS_LEGACY, language="python",
                    status=FileStatus.QUEUED, ai_source="", raw_traceback="",
                    target_ai_source=BATCH_HELPERS_AI, target_traceback=BATCH_HELPERS_TRACEBACK, target_status=FileStatus.FAILED),
    ]