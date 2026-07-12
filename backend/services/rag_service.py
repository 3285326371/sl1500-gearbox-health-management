import os
import re
import json
from dataclasses import dataclass
from urllib import request as urlrequest

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


def load_local_env():
    env_path = ENV_PATH
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().lstrip("\ufeff")
            os.environ.setdefault(key, value.strip().strip('"').strip("'"))


if load_dotenv:
    load_dotenv(ENV_PATH, encoding="utf-8-sig")
else:
    load_local_env()


@dataclass
class KnowledgeItem:
    id: str
    title: str
    topic: str
    keywords: tuple
    content: str


class KnowledgeBaseRAG:
    """面向 SL1500 齿轮箱运维场景的本地专家问答引擎。"""

    def __init__(self):
        self.last_api_error = ""
        self.knowledge_repo = [
            KnowledgeItem(
                id="KB-TEMP-01",
                title="油温过高排查",
                topic="temperature",
                keywords=("油温", "温度", "过温", "散热器", "冷却", "三通阀", "风扇"),
                content="油温超过 75°C 应关注冷却效率，超过 85°C 应按严重告警处理。优先检查散热器堵塞、冷却风扇、三通阀开度、油冷电机和环境风沙积尘。",
            ),
            KnowledgeItem(
                id="KB-VIB-01",
                title="高速轴承冲击诊断",
                topic="vibration",
                keywords=("轴承", "高速轴", "冲击", "峭度", "包络", "120", "240", "异响"),
                content="高速轴承疲劳剥落通常表现为峭度、峰值因子和包络峰值升高，可结合 120-240Hz 特征频率、包络谱和内窥镜复核滚道状态。",
            ),
            KnowledgeItem(
                id="KB-GEAR-01",
                title="齿面磨损与点蚀",
                topic="gear",
                keywords=("齿轮", "齿面", "点蚀", "磨损", "啮合", "铁谱", "金属颗粒"),
                content="齿面疲劳磨损常伴随啮合频率及边频带增强，建议结合油液铁谱、磁性堵塞物、金属颗粒浓度和齿面接触斑检查。",
            ),
            KnowledgeItem(
                id="KB-GEAR-02",
                title="齿轮断齿与啮合异常",
                topic="gear_damage",
                keywords=("断齿", "啮合异常", "齿轮断裂", "啮合冲击", "边频带", "齿侧间隙"),
                content="齿轮断齿属于严重故障，通常伴随周期性强冲击、啮合频率异常和金属磨粒增加，应立即降载或停机复核；啮合异常需检查齿侧间隙、接触斑、载荷波动和齿轮安装状态。",
            ),
            KnowledgeItem(
                id="KB-BEARING-02",
                title="轴承磨损、点蚀和高速端过温",
                topic="bearing",
                keywords=("轴承磨损", "轴承点蚀", "轴承剥落", "高速轴承", "高速端", "滚道", "保持架", "游隙"),
                content="轴承类故障包括磨损、点蚀、剥落和高速轴承过温。磨损多表现为振动 RMS 缓慢升高；点蚀/剥落会带来峭度、峰值因子和包络峰值升高；高速端过温需同步检查润滑、游隙、冷却和温度测点。",
            ),
            KnowledgeItem(
                id="KB-OIL-01",
                title="润滑油污染与油液劣化",
                topic="lubrication",
                keywords=("润滑油", "油液", "污染", "劣化", "NAS", "水分", "黏度", "滤芯", "呼吸器"),
                content="润滑油污染或劣化会加速齿轮和轴承磨损。应取样复测 NAS 等级、水分、黏度和金属颗粒，检查滤芯、呼吸器、密封、油位和磁性堵塞物。",
            ),
            KnowledgeItem(
                id="KB-ALIGN-01",
                title="联轴器不对中",
                topic="alignment",
                keywords=("联轴器", "不对中", "对中", "低频", "径向", "轴向", "找正"),
                content="联轴器不对中常表现为低频振动能量升高，伴随径向或轴向振动异常。应复核发电机与齿轮箱轴线、地脚螺栓、弹性体磨损和热态偏移。",
            ),
            KnowledgeItem(
                id="KB-LOOSE-01",
                title="箱体或基础松动",
                topic="looseness",
                keywords=("箱体", "基础", "松动", "地脚螺栓", "弹性支撑", "安装", "支撑"),
                content="箱体或基础松动常表现为宽频振动升高、低频成分增强和工况变化下振动波动。应检查地脚螺栓、弹性支撑、基础连接、齿轮箱支座和水平/垂直振动差异。",
            ),
            KnowledgeItem(
                id="KB-FAULT-LIST-01",
                title="齿轮箱故障全覆盖清单",
                topic="fault_catalog",
                keywords=("齿轮箱故障", "有哪些", "分类", "故障类型", "全部", "常见故障"),
                content="本系统覆盖的齿轮箱常见故障包括：齿轮齿面磨损、齿面点蚀/剥落、齿轮断齿、轴承磨损、轴承点蚀/剥落、高速轴承过温、齿轮箱油温过高、润滑油污染/油液劣化、轴系不对中、齿轮啮合异常、箱体或基础松动、冷却系统故障。",
            ),
            KnowledgeItem(
                id="KB-RUL-01",
                title="剩余寿命评估",
                topic="life_prediction",
                keywords=("寿命", "RUL", "剩余", "预测", "健康评分", "退化"),
                content="剩余寿命应结合健康评分、风险因子趋势和近 7-30 天退化速度估算。RUL 低于 30 天建议安排检修窗口，低于 7 天建议停机复核。",
            ),
            KnowledgeItem(
                id="KB-ALGO-01",
                title="M-IALO-SVR 方法",
                topic="algorithm",
                keywords=("M-IALO", "SVR", "算法", "模型", "预测", "优化"),
                content="M-IALO-SVR 可理解为使用改进优化算法搜索 SVR 超参数，适合小样本、非线性油温残差或寿命趋势预测。工程应用中要配合滑动窗口、残差阈值和交叉验证防止过拟合。",
            ),
            KnowledgeItem(
                id="KB-MAINT-01",
                title="检修策略",
                topic="maintenance",
                keywords=("检修", "维护", "工单", "备件", "巡检", "处理", "建议"),
                content="严重告警应形成工单并明确责任人、复测项和检修窗口。警告级别建议先做复测、趋势确认和油液分析，避免仅凭单点数据停机。",
            ),
        ]

    def _api_key(self):
        return os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")

    def _api_base_url(self):
        return (
            os.getenv("DASHSCOPE_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        ).rstrip("/")

    def _api_model(self):
        return os.getenv("DASHSCOPE_QA_MODEL") or os.getenv("OPENAI_QA_MODEL") or "qwen-plus"

    def _api_provider_name(self):
        base_url = self._api_base_url()
        if "dashscope.aliyuncs.com" in base_url:
            return "DashScope compatible API"
        return "OpenAI compatible API"

    def detect_intent(self, question):
        question = question.lower()
        if "故障" in question and any(word in question for word in ("哪些", "有哪些", "分类", "类型", "清单")):
            return "fault_catalog"
        if any(word in question for word in ("算法", "模型", "m-ialo", "svr", "原理")):
            return "algorithm"
        if any(word in question for word in ("怎么办", "如何", "怎么", "排查", "处理", "建议")):
            return "troubleshooting"
        if any(word in question for word in ("原因", "为什么", "导致", "机理")):
            return "root_cause"
        if any(word in question for word in ("寿命", "rul", "多久", "什么时候", "检修")):
            return "life_prediction"
        if any(word in question for word in ("状态", "是否正常", "健康", "风险")):
            return "status_review"
        return "expert_answer"

    def query(self, question, top_k=4):
        question_lower = question.lower()
        tokens = set(re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]{2,}", question_lower))
        results = []
        intent = self.detect_intent(question)

        for item in self.knowledge_repo:
            score = 0.0
            matched = []
            if intent == "fault_catalog" and item.topic == "fault_catalog":
                score += 5.0
            for keyword in item.keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in question_lower:
                    score += 2.0
                    matched.append(keyword)
            for token in tokens:
                if token and token in item.content.lower():
                    score += 0.4
            if score > 0:
                results.append((item, score, matched))

        if not results:
            results = [(item, 0.3, []) for item in self.knowledge_repo[:2]]

        results.sort(key=lambda row: row[1], reverse=True)
        return results[:top_k]

    def assess_status(self, status):
        oil_temp = float(status.get("oil_temp") or 0)
        vibration = float(status.get("vibration_rms") or 0)
        oil_quality = float(status.get("oil_quality") or 0)
        power = float(status.get("power") or 0)
        health_score = float(status.get("health_score") or 0)
        predicted_rul = float(status.get("predicted_rul_days") or 0)

        findings = []
        severity = "正常"

        if oil_temp >= 85:
            findings.append("油温达到严重告警区间，应优先排查散热与油冷回路。")
            severity = "严重"
        elif oil_temp >= 75:
            findings.append("油温进入预警区间，需要观察负荷、环境温度和冷却效率。")
            severity = "警告"

        if vibration >= 6:
            findings.append("振动有效值偏高，建议结合包络谱和频谱确认机械冲击来源。")
            severity = "严重"
        elif vibration >= 4.5:
            findings.append("振动接近或超过预警阈值，建议复测并排除安装松动。")
            if severity == "正常":
                severity = "警告"

        if oil_quality >= 10:
            findings.append("油液颗粒度偏高，建议取样复检并检查滤芯与磁性堵塞物。")
            if severity == "正常":
                severity = "警告"

        if not findings:
            findings.append("当前油温、振动和油液指标处于可控范围。")

        return {
            "severity": severity,
            "oil_temp": oil_temp,
            "vibration_rms": vibration,
            "oil_quality": oil_quality,
            "power": power,
            "health_score": health_score,
            "predicted_rul_days": predicted_rul,
            "findings": findings,
        }

    def build_actions(self, intent, status_review, docs, latest_fault=None):
        actions = []
        topics = {item.topic for item, _score, _matched in docs}

        if latest_fault and latest_fault.get("severity") in ("警告", "严重"):
            actions.append(f"复核最近诊断记录：{latest_fault.get('fault_type')}，置信度约 {latest_fault.get('probability', 0)}%。")

        if "temperature" in topics or status_review["oil_temp"] >= 75:
            actions.extend([
                "检查散热器表面是否被柳絮、风沙或油污堵塞。",
                "确认冷却风扇、油冷电机、三通阀和温控开关动作是否正常。",
            ])

        if "vibration" in topics or status_review["vibration_rms"] >= 4.5:
            actions.extend([
                "导出近 10 分钟振动波形，比较 RMS、峭度、峰值因子和包络峰值。",
                "对 120-240Hz 区间做包络谱复核，必要时安排内窥镜检查。",
            ])

        if "alignment" in topics:
            actions.extend([
                "检查联轴器弹性体、地脚螺栓和热态对中偏移。",
                "对比水平、垂直和轴向振动，确认是否存在 1X/2X 低频增强。",
            ])

        if "gear" in topics or "gear_damage" in topics:
            actions.extend([
                "取油样做铁谱分析，关注金属颗粒浓度和磁性堵塞物。",
                "检查齿面接触斑、点蚀和啮合频率边频带。",
            ])
            if "gear_damage" in topics:
                actions.insert(0, "若怀疑断齿或强啮合冲击，先降载运行并准备停机内窥镜复核。")

        if "bearing" in topics:
            actions.extend([
                "复核轴承测点 RMS、峭度、峰值因子和包络峰值趋势。",
                "检查轴承润滑、游隙、滚道状态和高速端温升。"
            ])

        if "lubrication" in topics:
            actions.extend([
                "取油样检测 NAS 等级、水分、黏度和金属磨粒。",
                "检查滤芯、呼吸器、密封、油位和磁性堵塞物。"
            ])

        if "looseness" in topics:
            actions.extend([
                "复核齿轮箱地脚螺栓、弹性支撑和基础连接。",
                "对比水平、垂直方向振动，确认是否存在宽频松动特征。"
            ])

        if "fault_catalog" in topics:
            actions.extend([
                "按齿轮、轴承、润滑、冷却、轴系和基础六类建立排查清单。",
                "先用油温、振动 RMS、峭度、包络峰值和油液 NAS 做初筛，再安排现场复核。"
            ])

        if intent == "life_prediction":
            actions.insert(0, self._build_recheck_advice(status_review))
            actions.append("结合近 7 天健康评分趋势更新 RUL，低于 30 天时提前锁定检修窗口。")

        if not actions:
            actions = [
                "保持常规巡检，继续观察油温、振动和油液颗粒度趋势。",
                "若连续两次出现同类异常，再升级为现场复检工单。",
            ]

        deduped = []
        for action in actions:
            if action not in deduped:
                deduped.append(action)
        return deduped[:6]

    def generate_answer_with_status(self, question, status=None, latest_fault=None, deep_thinking=False):
        local_result = self._generate_local_answer(question, status, latest_fault)
        if not deep_thinking:
            return local_result

        api_answer = self._generate_deep_answer(question, status or {}, latest_fault, local_result)
        if not api_answer:
            local_result["deep_thinking"] = False
            local_result["engine"] = "local_fallback"
            local_result["api_status"] = (
                "API key is not configured; using local expert rules."
                if not self._api_key()
                else f"API call failed; using local expert rules. Check key, model, or base URL. {self.last_api_error}"
            )
            return local_result

        local_result.update({
            "answer": api_answer,
            "confidence": max(local_result["confidence"], 0.88),
            "deep_thinking": True,
            "engine": "compatible_api",
            "model": self._api_model(),
            "api_status": f"model-first via {self._api_provider_name()}",
        })
        return local_result

    def stream_answer_with_status(self, question, status=None, latest_fault=None, deep_thinking=False):
        local_result = self._generate_local_answer(question, status, latest_fault)
        base_meta = {
            "sources": local_result.get("sources", []),
            "intent": local_result.get("intent"),
            "confidence": local_result.get("confidence"),
            "risk_level": local_result.get("risk_level"),
            "suggested_questions": local_result.get("suggested_questions", []),
        }

        if not deep_thinking or not self._api_key():
            answer = local_result.get("answer", "")
            api_status = (
                "local expert rules"
                if not deep_thinking
                else "API key is not configured; using local expert rules."
            )
            yield "meta", {**base_meta, "engine": "local_fallback" if deep_thinking else "local_expert", "api_status": api_status}
            for chunk in self._chunk_text(answer):
                yield "delta", {"text": chunk}
            yield "done", {**base_meta, "answer": answer, "engine": "local_fallback" if deep_thinking else "local_expert", "api_status": api_status}
            return

        yielded_text = []
        yield "meta", {**base_meta, "engine": "compatible_api", "model": self._api_model(), "api_status": f"streaming via {self._api_provider_name()}"}
        try:
            for chunk in self._stream_deep_answer(question, status or {}, latest_fault, local_result):
                if not chunk:
                    continue
                yielded_text.append(chunk)
                yield "delta", {"text": chunk}
        except Exception as exc:
            self.last_api_error = f"error: {exc}"
            fallback = local_result.get("answer", "")
            yielded_text = []
            yield "meta", {**base_meta, "engine": "local_fallback", "api_status": f"API stream failed; using local expert rules. {self.last_api_error}"}
            for chunk in self._chunk_text(fallback):
                yielded_text.append(chunk)
                yield "delta", {"text": chunk}

        answer = "".join(yielded_text) or local_result.get("answer", "")
        yield "done", {
            **base_meta,
            "answer": answer,
            "confidence": max(local_result.get("confidence", 0), 0.88) if yielded_text else local_result.get("confidence"),
            "deep_thinking": bool(yielded_text),
            "engine": "compatible_api" if yielded_text else "local_fallback",
            "model": self._api_model() if yielded_text else None,
            "api_status": f"streaming via {self._api_provider_name()}" if yielded_text else "local expert rules",
        }

    def _chunk_text(self, text, size=12):
        text = str(text or "")
        for index in range(0, len(text), size):
            yield text[index:index + size]

    def _generate_local_answer(self, question, status=None, latest_fault=None):
        status = status or {}
        intent = self.detect_intent(question)
        docs = self.query(question)
        status_review = self.assess_status(status)
        actions = self.build_actions(intent, status_review, docs, latest_fault)

        top_docs = [item for item, _score, _matched in docs]
        confidence = min(0.96, 0.58 + sum(score for _item, score, _matched in docs[:3]) * 0.08)

        answer_parts = [
            f"结论：{self._build_conclusion(intent, status_review, top_docs, latest_fault)}",
            "",
            "实时工况："
            f"油温 {status_review['oil_temp']:.1f}°C，"
            f"振动 {status_review['vibration_rms']:.2f} mm/s，"
            f"油液 NAS {status_review['oil_quality']:.1f}，"
            f"功率 {status_review['power']:.0f} kW。",
            "",
            "判断依据：",
        ]

        answer_parts.extend([f"- {finding}" for finding in status_review["findings"]])
        for item in top_docs[:3]:
            answer_parts.append(f"- {item.content}")

        answer_parts.extend(["", "建议步骤："])
        answer_parts.extend([f"{idx}. {action}" for idx, action in enumerate(actions, start=1)])

        followups = self._suggest_followups(intent, top_docs)
        answer_parts.extend(["", "可继续追问："])
        answer_parts.extend([f"- {item}" for item in followups])

        return {
            "answer": "\n".join(answer_parts),
            "sources": [
                {"id": item.id, "title": item.title, "topic": item.topic}
                for item in top_docs
            ],
            "intent": intent,
            "confidence": round(confidence, 2),
            "risk_level": status_review["severity"],
            "suggested_questions": followups,
            "deep_thinking": False,
            "engine": "local_expert",
            "api_status": "local expert rules",
        }

    def _generate_deep_answer(self, question, status, latest_fault, local_result):
        api_key = self._api_key()
        if not api_key:
            return None

    def _deep_messages(self, question, status, latest_fault, local_result):
        return [
            {
                "role": "system",
                "content": (
                    "You are a senior wind turbine gearbox maintenance diagnostic assistant for an SL1500 health management system. "
                    "Use the live telemetry as the primary evidence. The knowledge base is only supplementary evidence, not the boundary of the answer. "
                    "Do not copy retrieved text mechanically. Do not reveal hidden reasoning. "
                    "Always answer in Chinese with: conclusion, risk level, key evidence, actionable steps, and work-order/report advice."
                ),
            },
            {
                "role": "user",
                "content": self._build_deep_prompt(question, status, latest_fault, local_result),
            },
        ]

    def _stream_deep_answer(self, question, status, latest_fault, local_result):
        api_key = self._api_key()
        if not api_key:
            return
        model = self._api_model()
        messages = self._deep_messages(question, status, latest_fault, local_result)
        try:
            import openai
        except ImportError:
            yield from self._stream_chat_completions_http(model, messages, api_key)
            return

        openai.api_key = api_key
        api_base = self._api_base_url()
        if api_base:
            openai.api_base = api_base

        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            temperature=0.25,
            max_tokens=1400,
            stream=True,
        )
        for part in response:
            choice = (part.get("choices") or [{}])[0]
            delta = choice.get("delta") or {}
            content = delta.get("content")
            if content:
                yield content

    def _stream_chat_completions_http(self, model, messages, api_key):
        base_url = self._api_base_url()
        endpoint = f"{base_url}/chat/completions"
        payload = json.dumps({
            "model": model,
            "messages": messages,
            "temperature": 0.25,
            "max_tokens": 1400,
            "stream": True,
        }).encode("utf-8")
        req = urlrequest.Request(
            endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=60) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="ignore").strip()
                if not line or not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    item = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choice = (item.get("choices") or [{}])[0]
                delta = choice.get("delta") or {}
                content = delta.get("content")
                if content:
                    yield content

        try:
            model = self._api_model()
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a senior wind turbine gearbox maintenance diagnostic assistant for an SL1500 health management system. "
                        "Use the live telemetry as the primary evidence. The knowledge base is only supplementary evidence, not the boundary of the answer. "
                        "Do not copy retrieved text mechanically. Do not reveal hidden reasoning. "
                        "Always answer in Chinese with: conclusion, risk level, key evidence, actionable steps, and work-order/report advice."
                    ),
                },
                {
                    "role": "user",
                    "content": self._build_deep_prompt(question, status, latest_fault, local_result),
                },
            ]
            try:
                import openai

                openai.api_key = api_key
                api_base = self._api_base_url()
                if api_base:
                    openai.api_base = api_base

                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    temperature=0.25,
                    max_tokens=1400,
                )
                return response["choices"][0]["message"]["content"].strip()
            except ImportError:
                return self._call_chat_completions_http(model, messages, api_key)
        except Exception as exc:
            self.last_api_error = f"error: {exc}"
            print(f"OpenAI QA fallback: {exc}")
            return None

    def _call_chat_completions_http(self, model, messages, api_key):
        base_url = self._api_base_url()
        endpoint = f"{base_url}/chat/completions"
        payload = json.dumps({
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1200,
        }).encode("utf-8")
        req = urlrequest.Request(
            endpoint,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlrequest.urlopen(req, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()

    def _build_deep_prompt(self, question, status, latest_fault, local_result):
        sources = local_result.get("source_documents") or local_result.get("sources") or []
        source_text = "\n".join(
            f"- {item.get('id', '')} {item.get('title', '')} / {item.get('topic', '')}"
            for item in sources
        ) or "No knowledge-base hit. Use live telemetry and general gearbox diagnostic principles."

        return f"""
User question: {question}

Live telemetry JSON:
{json.dumps(status, ensure_ascii=False, indent=2)}

Latest diagnostic record:
{latest_fault or "None"}

Supplementary knowledge sources, for evidence only:
{source_text}

Answer in Chinese. Keep it concise: no more than 650 Chinese characters unless the user asks for details. Use this exact structure and keep the Chinese headings:
结论： directly answer whether the unit is normal, whether shutdown is needed, and whether a work order is needed.
风险等级： 正常 / 关注 / 警告 / 严重, with trigger reasons.
关键依据： 2-4 bullets using oil temperature, vibration RMS, oil NAS, power, health score, RUL, or latest fault record.
建议步骤：
1. First field or system verification action.
2. Second trend, spectrum, oil sample, or threshold verification action.
3. Third maintenance, work-order, or report action.
后续追问： provide 2 clickable next questions.
""".strip()

    def _build_conclusion(self, intent, status_review, docs, latest_fault):
        if intent == "life_prediction":
            return self._build_recheck_advice(status_review)
        if intent == "algorithm":
            return "M-IALO-SVR 在油温残差预测中用于自动寻找 SVR 的最优参数，再用“实测油温 - 预测正常油温”的残差判断冷却效率退化；工程上建议以 7-30 天滑动窗口训练，并把残差连续超限作为油冷系统预警。"
        if intent == "fault_catalog" or (docs and docs[0].topic == "fault_catalog"):
            return "齿轮箱故障主要包括齿轮、轴承、润滑、冷却、轴系和基础六类，本系统已覆盖 12 种常见异常。"
        if latest_fault and latest_fault.get("severity") in ("警告", "严重"):
            return f"结合最近诊断，当前重点风险是“{latest_fault.get('fault_type')}”，建议按 {latest_fault.get('severity')} 级别处理。"
        if status_review["severity"] != "正常":
            return f"当前存在{status_review['severity']}级运行风险，应先处理实时超限项，再做趋势复核。"
        if docs:
            return self._build_topic_conclusion(docs[0], intent, status_review)
        return "当前资料不足以给出单一故障结论，建议补充油温、振动频谱或油液数据。"

    def _build_topic_conclusion(self, doc, intent, status_review):
        topic_conclusions = {
            "temperature": "油温类问题应先判断是否超过 75°C/85°C 两级阈值；当前未超限时按趋势观察，若升温伴随功率下降，应优先查散热器、三通阀、油冷电机和冷却风扇。",
            "vibration": "振动异响应优先做频谱和包络谱复核；若 RMS、峭度或包络峰值升高，重点排查高速轴承冲击、齿面点蚀和安装松动。",
            "gear": "齿面类风险不能只看单点振动，应结合啮合频率边频带、油液铁谱和磁性堵塞物判断；当前未超限时建议纳入 7 天趋势跟踪。",
            "gear_damage": "齿轮断齿和啮合异常属于重点风险，应先看周期性强冲击、啮合频率边频带和金属磨粒；疑似断齿时建议降载或停机复核。",
            "bearing": "轴承类故障应分清磨损、点蚀/剥落和过温：磨损看 RMS 趋势，点蚀/剥落看峭度和包络峰值，高速端过温还要核查润滑与冷却。",
            "lubrication": "润滑油污染或劣化会加速齿轮和轴承退化，应结合 NAS 等级、水分、黏度、金属颗粒和滤芯状态判断。",
            "alignment": "联轴器不对中应重点看 1X/2X 低频增强和轴向/径向振动差异；当前未超限时建议在下次巡检中复核热态对中和地脚螺栓。",
            "looseness": "箱体或基础松动通常表现为宽频振动和低频增强，应优先检查地脚螺栓、弹性支撑、基础连接和支座状态。",
            "fault_catalog": "齿轮箱故障可归为齿轮、轴承、润滑、冷却、轴系和基础六大类；本系统已覆盖齿面磨损/点蚀/断齿、轴承磨损/剥落/过温、油温过高、油液劣化、轴系不对中、啮合异常、基础松动和冷却系统故障。",
            "maintenance": "维护策略应按风险等级分层：正常 30 天例行复检，警告 7 天内复检，严重 24 小时内现场复核并生成工单。",
            "life_prediction": self._build_recheck_advice(status_review),
            "algorithm": "M-IALO-SVR 适合做油温残差预测和 RUL 趋势估计，输出应与阈值告警、趋势斜率和现场检修记录共同校验。",
        }
        return topic_conclusions.get(doc.topic, f"该问题可按“{doc.title}”处理：先确认实时阈值，再结合趋势和现场复测给出维护动作。")

    def _build_recheck_advice(self, status_review):
        health_score = status_review.get("health_score") or 0
        predicted_rul = status_review.get("predicted_rul_days") or 0
        severity = status_review.get("severity")

        if predicted_rul and predicted_rul <= 7:
            return f"建议 24 小时内复检，并准备停机复核；当前 RUL 约 {int(predicted_rul)} 天。"
        if predicted_rul and predicted_rul <= 30:
            return f"建议 3 天内复检并锁定检修窗口；当前 RUL 约 {int(predicted_rul)} 天。"
        if health_score and health_score < 60:
            return f"建议 24 小时内复检；当前健康评分 {int(health_score)} 分，已进入高风险区。"
        if health_score and health_score < 80:
            return f"建议 7 天内复检；当前健康评分 {int(health_score)} 分，需要跟踪退化趋势。"
        if severity == "严重":
            return "建议 24 小时内复检，并同步生成现场排查工单。"
        if severity == "警告":
            return "建议 7 天内复检，重点复测油温、振动和油液颗粒度趋势。"
        if health_score:
            return f"建议按 30 天周期安排例行复检；当前健康评分 {int(health_score)} 分，未见明显超限。"
        return "建议按 30 天周期安排例行复检；若连续两次出现油温、振动或油液异常，则提前到 7 天内复检。"

    def _suggest_followups(self, intent, docs):
        topics = {item.topic for item in docs}
        suggestions = []
        if "temperature" in topics:
            suggestions.append("油温超过 85°C 时是否需要立即停机？")
        if "vibration" in topics:
            suggestions.append("如何根据峭度和包络峰值区分轴承与齿面故障？")
        if "alignment" in topics:
            suggestions.append("联轴器不对中和轴承故障在频谱上如何区分？")
        if intent != "life_prediction":
            suggestions.append("当前健康评分下应该多久安排一次复检？")
        if intent != "algorithm":
            suggestions.append("M-IALO-SVR 在油温残差预测中怎么使用？")
        return suggestions[:3]


rag_system = KnowledgeBaseRAG()
