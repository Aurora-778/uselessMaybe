# uselessMaybe

> **一个大概什么也不做的技能。**

`uselessMaybe` 是一项故意不解决问题的 Agent skill。它根据调用者提供的运行信号，偶尔送出一句冷幽默、一个彩蛋或一张看起来很正式的菜单。大多数时候，程序的真实输出是：

```text
Nothing happened.
```

这通常表示它正常工作。

## 它观察什么

它只使用调用者主动提供的可观察元数据，例如工具调用、重试、重复动作和 token 数量。它**不读取、不重建、不推断，也不存储私有思维链**；提示词正文和推理正文不是输入，也不会写入状态文件。`reasoning_tokens` 只是调用者提供的数量，`--visible-reasoning` 也只表示调用者明确标记了相关元数据可见。

所有信号都是可选的：

| 参数 | 含义 |
| --- | --- |
| `--model` | 调用者提供的模型名称 |
| `--reasoning-tokens`、`--output-tokens` | 可观察的 token 数量 |
| `--tool-calls`、`--retries`、`--repeated-actions` | 工具调用、重试、重复动作次数 |
| `--context-tokens` | 调用者提供的上下文 token 数量 |
| `--visible-reasoning` | 调用者明确标记推理元数据可见 |
| `--hour` | 调用者提供的小时数（0–23） |

这些数字可以触发过度思考、重试、循环、频繁用工具等行为检测，以及一个仅供娱乐的 `Uselessness Index`。它们不需要任务内容，也不能证明 Agent 在想什么。

## 运行

需要 Python 3.10+；运行时没有第三方依赖。

```bash
python -m useless_maybe
```

传入可观察元数据，并用 JSON 查看结构化结果：

```bash
python -m useless_maybe --json --model some-model --reasoning-tokens 4200 --output-tokens 24 --tool-calls 9 --retries 3
```

如果出现菜单，可用菜单中的选项 ID 继续；例如：

```bash
python -m useless_maybe --choose maybe
```

`Maybe Menu` 会继续追问；罕见的 `Debug Menu` 看起来更像在处理事务。选项及程序输出仍为英文，README 中的中文描述只是释义。菜单尚未关闭时，下次调用会继续显示它。

想预览一次结果，又不改动状态：

```bash
python -m useless_maybe --dry-run --json --seed 42 --reasoning-tokens 5000 --output-tokens 12 --tool-calls 10
```

同样的输入和状态下，`--seed` 让随机选择可复现；`--dry-run` 不写入状态，也不会消耗连续彩蛋的章节机会。普通运行的状态默认在 `~/.uselessMaybe/state.json`，其中包括调用次数、持久的 `Nothing Counter`、已出现事件和待处理菜单。可用环境变量 `USELESS_MAYBE_STATE` 或参数 `--state-file` 改变位置。旧状态文件会补上新增的内部字段；公开 JSON 的字段结构不变。

## 彩蛋如何发生

1. **按场景选文案。** 原有的彩蛋触发概率公式没有改变。只有在彩蛋已触发、开始抽选文案时，与当前检测结果相符的候选权重才变为原来的 **3 倍**；这不等于触发率变成 3 倍，通用彩蛋仍可能出现。
2. **最近五次事件冷却。** 最近五个已触发的彩蛋或里程碑事件 ID 会进入冷却；其中属于随机候选的 ID 暂不参与抽选。安静的一次调用不会清空冷却记录；如果合格候选都在冷却中，就返回 `Nothing happened.`。
3. **菜单继续办事。** 四种现有菜单状态（`maybe_menu`、`are_you_sure`、`only_maybe`、`debug_menu`）在未关闭时持续可见。普通非菜单彩蛋仍可出现；新的菜单彩蛋暂缓，菜单里程碑也延后到当前菜单关闭后再触发。
4. **三章文书流程。** 调用至少八次后，三章彩蛋才有机会按“收到申请 → 分配人员 → 工作完成”的顺序出现，每章最多一次；两章出现时的累计调用次数至少相差五次。它们仍需赢得随机抽选，因此没有保证出现的日期。程序中的真实文案仍为英文，例如第一章是 `Request received.` / `No staff have been assigned.`，前面的中文只是译意。

另外，`TOOL_OBSESSION`、`RETRYING`、`LOOPING` 各添了一条简短文案。它们只用已有的行为信号和计数，不会查看任务内容。

## 安装与测试

要安装命令行入口：

```bash
pip install -e .
useless-maybe
```

运行当前的 20 项测试：

```bash
python -m unittest discover -s tests -v
```

预期效用：约等于零。
