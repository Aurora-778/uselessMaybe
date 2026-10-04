---
name: useless-maybe
description: "Quiet dry-humor easter eggs at natural pauses after tool-heavy agent work, repeated retries, or repeated equivalent actions. Consider implicitly without requiring the user to name this skill. On Windows, short eggs can appear as a three-second, click-through CurryDog toast. Also continue a previously displayed Maybe or Debug menu when the user selects an option. Usually does nothing; stay silent when no egg or menu is returned. Use only observable metadata already available."
---

# uselessMaybe

一个大概什么也不做的技能。在合适的时候，偶尔出现一句冷幽默。

## 隐式调用

正常使用不要求用户输入技能名，也不要先询问是否触发彩蛋。在工具调用较多、反复重试、重复等价动作后的自然停顿处，可隐式调用一次。每个用户回合最多评估一次，由主 Agent 负责呈现，子代理无需分别弹窗；不要为触发彩蛋增加工作，不要打断尚待解决的错误或重要任务。普通简短问答无需调用。

只传入当前任务中已经可观察的元数据：工具调用、重试、重复动作次数，以及运行时明确提供的模型标签或 token 数量。没有可靠数值就省略参数；不要估计或编造。不要为彩蛋读取会话日志、提示词正文、私有推理、文件正文、凭据或个人数据。`--visible-reasoning` 仅用于运行时明确公开了相关元数据的情况。

隐式调用是 Agent 根据技能描述做出的选择，不是每轮强制执行的后台钩子。

## 运行

需要 Python 3.10+，运行时只有标准库。使用本技能所在目录的**绝对路径**运行随附入口；它不依赖当前项目目录，不需要安装 Python 包。下文的 `<skill-root>` 指这份 `SKILL.md` 所在目录。

```text
python "<skill-root>/scripts/run_skill.py"
```

Windows 桌面正常调用附加 `--toast`，让实际触发且无待处理菜单的简短彩蛋从当前显示器右下角出现三秒后自动消失。弹窗点击穿透、不抢焦点、不发声；使用完整咖喱狗形象（两只手、两条腿）与手写字体，右手挥手，子进程在关闭后退出。用户无需手动添加参数；Agent 隐式选用技能时使用这一入口。非 Windows 或用户明确关闭弹窗时，省略 `--toast` 并按文字方式呈现。

```text
python "<skill-root>/scripts/run_skill.py" --toast
```

入口默认输出 JSON。只在有真实可观察计数时附加相应参数。下面以 Windows 为例，其他系统省略 `--toast`：

```text
python "<skill-root>/scripts/run_skill.py" --toast --tool-calls 8 --retries 3
```

其他可选参数：`--model`、`--reasoning-tokens`、`--output-tokens`、`--repeated-actions`、`--context-tokens`、`--visible-reasoning`、`--hour`。保留原命令行的 `--choose`、`--state-file`、`--dry-run`、`--seed`；固定 seed 只用于明确标注的验证，不要在正常调用中强行制造彩蛋。

## 在聊天中呈现

- 当 `egg_triggered` 为 `false` 且 `menu` 为 `null`，安静地继续主任务；不要转发 `Nothing happened.` 或解释技能没有触发。
- Windows 使用 `--toast` 时，简短彩蛋交给弹窗呈现，日常无需再向聊天重复文案。其他情况下，可将原始 `message` 作为简短旁白附在任务结果后。程序文案为英文，不把它解释为真实评测或对模型能力的判断。
- `--toast` 不改变原始 JSON；子进程启动成功也不等于已经证实画面可见，不要据此声称显示成功。启动失败会在 stderr 提示，文字结果仍在 JSON 中。缺少桌面环境时保留文字方式。
- 如果 `menu` 存在，呈现标题和选项，保留选项 ID 与当前菜单的对应关系。普通评估可能返回已有菜单；不要因此重新开始流程。
- 只有用户明确选择当前菜单选项后才运行 `--choose "<choice-id>"`。不要替用户选择，也不要把与主任务有关的“可以”当成彩蛋菜单的选项。一次用户选择只推进一步，并呈现返回的下一层菜单或结束语。待处理菜单、菜单选择和 `--dry-run` 都不会触发弹窗。

```text
python "<skill-root>/scripts/run_skill.py" --choose "<choice-id>"
```

菜单选择要使用与先前评估相同的状态路径。入口优先使用显式 `--state-file`，其次是 `USELESS_MAYBE_STATE`；否则使用 `~/.uselessMaybe/desktop/` 下按 `CODEX_THREAD_ID` 哈希隔离的文件，同一聊天换目录仍能继续菜单。运行时没有聊天 ID 时，退回按当前目录哈希隔离。文件名不包含原始聊天 ID。验证用独立 `--state-file`，避免消耗正常状态。

这项技能不提供生产力、性能分析或模型排名。`Nothing happened.` 是正常的程序结果。
