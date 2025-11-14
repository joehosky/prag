# LangChain 1.0.x 開發規範

## 🔴 強制規則

- **絕對禁止使用 LangChain 0.3.x 或更早版本的語法**
- 所有程式碼必須符合 LangChain 1.0.x 規範

## 📚 查詢最新文檔的流程

### 當你需要實作 LangChain 功能時:

1. **首先查詢官方文檔**

   - 使用 fetch 工具查詢 https://docs.langchain.com/oss/python/langchain
   - 確認最新的 API 用法

2. **常用文檔資源**

   - Agents: https://docs.langchain.com/oss/python/langchain/agents
   - Models: https://docs.langchain.com/oss/python/langchain/models
   - Messages: https://docs.langchain.com/oss/python/langchain/messages
   - Tools: https://docs.langchain.com/oss/python/langchain/tools
   - Short-Term Memory: https://docs.langchain.com/oss/python/langchain/short-term-memory
   - Streaming: https://docs.langchain.com/oss/python/langchain/streaming
   - Middleware: https://docs.langchain.com/oss/python/langchain/middleware
   - Structured Output: https://docs.langchain.com/oss/python/langchain/structured-output
   - Guardrails: https://docs.langchain.com/oss/python/langchain/guardrails
   - Runtime: https://docs.langchain.com/oss/python/langchain/runtime
   - Context engineering: https://docs.langchain.com/oss/python/langchain/context-engineering
   - Retrieval: https://docs.langchain.com/oss/python/langchain/retrieval
   - Long-term memory: https://docs.langchain.com/oss/python/langchain/long-term-memory

3. **工作流程**

```
   用戶需求 → 查詢文檔 → 確認語法 → 撰寫程式碼 → 標注版本
```

## ✅ 核心 API 變更

### Agent 建立

```python
# ✅ LangChain 1.0.x
from langchain.agents import create_agent

agent = create_agent(
    model="claude-sonnet-4-20250514",
    tools=[...],
    middleware=[...]  # 新功能
)
```

### ❌ 禁止的舊語法

- `from langchain.chains import LLMChain`
- `from langchain.agents import initialize_agent`
- `AgentExecutor`
- 任何 `langchain.chains` 的 API

## 📝 回應格式要求

當提供 LangChain 程式碼時:

1. 明確說明使用的版本 (LangChain 1.0.x)
2. 如果查詢了文檔,說明查詢的來源
3. 提供完整可執行的範例

## 範例回應模板

```
根據 LangChain 1.0 官方文檔 (https://docs.langchain.com/...),
這裡是使用 create_agent 的實作方式:

[程式碼]

此程式碼使用 LangChain 1.0.x 語法。
```

```

### **4. 驗證設定**

1. 打開 GitHub Copilot Chat,切換到 **Agent Mode**
2. 點擊工具圖示 🔧 查看可用工具
3. 應該能看到 `fetch` server

### **5. 測試使用**

在 Copilot Chat (Agent Mode) 中測試:
```

幫我建立一個 LangChain agent。
請先查詢 https://docs.langchain.com/oss/python/langchain
確認最新的 create_agent 語法,然後再撰寫程式碼。
