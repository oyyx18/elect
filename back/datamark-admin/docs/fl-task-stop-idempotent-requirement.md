# FL Task Stop Idempotent Fix

## 要修什么

修复联邦训练任务的状态不一致问题：

- 后端任务还是 `RUNNING`
- 但 Runner 实际已经没有在跑
- 前端点停止时，后端返回“没有正在运行的任务”
- 结果任务一直卡在 `RUNNING`
- 新任务可能无法启动

前端现在只做了 UI 收口，真正的状态修复要由后端完成。

## 目标行为

把 `POST /api/fl-tasks/{taskId}/stop` 做成幂等停止接口。

要求：

- 如果目标任务正在真实运行：正常停止，状态改成 `STOPPED`
- 如果目标任务数据库里还是 `RUNNING`，但 Runner 已经没在跑：也返回成功，状态改成 `STOPPED`
- 如果 Runner 当前跑的是别的任务：不能误停别的任务；当前目标任务如果确认不是活动任务，也要能收口成 `STOPPED`
- 如果 Runner 不可访问：返回明确错误，不要盲目改成 `STOPPED`

## 接口约束

接口不变：

`POST /api/fl-tasks/{taskId}/stop`

返回结构不变，不加新字段：

```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "taskId": "fl_xxx",
    "status": "STOPPED"
  }
}
```

关键语义：

- “目标任务已经不在运行”不应该再返回失败
- 只要 Runner 可访问，且能确认该任务不是当前活动任务，就应按成功收口

## 最小实现要求

实现 stop 时按这个顺序处理：

1. 读取目标任务
2. 查询 Runner 当前状态
3. 用 Runner 的 `running` 和 `activeTaskId` 判断目标任务是否真的在运行
4. 如果目标任务真的在运行：
   - 调用 Python 停止逻辑
   - 成功后落库 `STOPPED`
5. 如果目标任务已经不在运行：
   - 不再报错
   - 直接把任务落库成 `STOPPED`
6. 如果 Runner 不可访问：
   - 返回明确错误
   - 不要猜测任务已经结束

落库时至少更新：

- `status = STOPPED`
- `finishedAt`，如果原来为空则补写
- 运行中占用状态 / 锁 / 活动任务缓存

## 注意点

- 判断真实运行态时，以 Runner 为准，不要只信数据库里的 `RUNNING`
- 不要因为 stop 的目标任务是残留 `RUNNING`，就去停止别的活动任务
- 这次修复不要求新增接口
- 这次修复不要求前端适配新字段

## 验收

至少通过这些场景：

1. 正常运行中的任务调用 stop 后返回成功，状态变成 `STOPPED`
2. `running = false` 且 `activeTaskId = null` 时，残留 `RUNNING` 任务调用 stop 也返回成功，且状态落库为 `STOPPED`
3. 当前真实运行的是别的任务时，不会误停别的任务
4. Runner 不可访问时，返回明确错误，不会误把任务改成 `STOPPED`
5. 修复后，前端刷新列表或详情时，后端直接返回正确状态，不再依赖前端本地收口
