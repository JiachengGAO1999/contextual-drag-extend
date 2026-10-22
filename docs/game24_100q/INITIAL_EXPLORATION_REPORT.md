# 初步探索状态（2026-10-14）

**NOT_STARTED：100题未完成、eligible dataset未冻结，development/held-out split未建立。** 本轮R0/R2/R3新生成数为0，因此无新准确率、恢复案例或bootstrap区间；旧论文87.0/39.1/78.3不能代替新数据复现。

待满足数据门槛后的预定分析：固定seed20261014划分20题development和至少80题held-out。development每题2paired seeds×R0/R2/R3，共120次；资源不足可先完成固定前10题的60次后审计。R2/R3必须复用同一failed draft、文本、位置、prefill和首token，R3从第2token起阻断draft直接KV读取；用实际元数据/首token校验该实现条件。

按全部development题统计R0−R2、R3−R2，恢复与损伤分别报告；每题先平均两个seed，5000次question-level bootstrap，保留finish reason、长度、截断率。不根据drag或R3恢复删题；held-out不参与调参。

RQ2优先在固定题目已有多草稿上做CPU描述；新增draft比较需事前冻结少量组合。RQ3来源/长度/最终错误类型/clean能力/基线错误频率先作探索性关联，不能当内部机制。当前2题不能支持稳定异质性；不运行X/CALC、局部mask或Gate0未通过的代理评分。
