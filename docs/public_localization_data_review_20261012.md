# 公开定位与纠错数据检查

状态：CPU资料检查，没有新增模型调用，没有确认新机制或方法MVP。

## 原论文与相关公开研究

原Contextual Drag公开仓库的完整文件目录共556个文件，本次按输出
目录、evaluated/response/generation文件名查找，未找到原跨模型完整
推理输出入口。README给的是重新生成流程；这项有界检查不能证明
作者在所有平台都未公开数据。Brackbill博客及其所链接的入口也尚未
找到完整实验轨迹；检查了作者公开仓库名及rl_toy、llama_training文件
目录，不能将作者博客中的比例当作本项目独立复现。

## 找到的独立资料入口

[Thought-ICS公开仓库](https://github.com/Ankur-Samanta/Thought_ICS)提供
166份缓存，共43,524,222字节。缓存文件数不等于独立题目数或实验数。
本次只下载按路径排序的首份缓存及方法说明、相关源码供阅读，不执行
外部代码、不下载模型。首份metadata指向llama8b、AMC23、40题，包含
分步chain、answer及作者的correct标签；未见错误位置、诊断理由或
修改后结果。作者正确性标签尚未独立重评。

文件与来源记录在
`outputs/generation-diagnostics-20261005/public_thought_ics_preview/`：
`repository_inventory.json`、`preview_summary.json`、原始缓存，以及
供阅读的upstream_README、self_correction.py、thought_mdp.py。
这些文件是公开资料预览，不是冻结执行题单。

## 对创新判断的实质约束

[论文](https://arxiv.org/html/2602.02416v1)及仓库已经把验证、定位、
回退重采样分开研究。其README和源码还提供 `--context`，在重采样时
保留上一次失败链和错误分析；README称小模型尚不能有效利用这类
显式反馈，主实验集中于从截断前缀重新采样。这是作者的报告，本次
没有获得该条件的完整结果，不能代替独立核验。

因此，单纯“分步定位后回退”“准确错误位置有帮助”或“保留失败链
仍有害”都不足以成为我们的新命题。更不能把已有回退/历史保留条件
换名后开一批GPU。缓存提供了未来独立材料的入口，但仍须一个可与
已有解释区分的预测，以及相应的诊断/纠错记录或新实验。

本次不启动Thought-ICS复现，不扩模型，不把公开初始链当作准确定位
后的续写。继续遵守原共享24 GPU小时预算。
