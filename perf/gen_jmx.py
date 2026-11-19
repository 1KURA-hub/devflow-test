"""生成 JMeter 测试计划（三个场景）。"""
import sys

TPL = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.6.3">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="{name}">
      <boolProp name="TestPlan.functional_mode">false</boolProp>
      <boolProp name="TestPlan.serialize_threadgroups">false</boolProp>
      <elementProp name="TestPlan.user_defined_variables" elementType="Arguments" guiclass="ArgumentsPanel" testclass="Arguments">
        <collectionProp name="Arguments.arguments"/>
      </elementProp>
    </TestPlan>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="tg">
        <stringProp name="ThreadGroup.on_sample_error">continue</stringProp>
        <elementProp name="ThreadGroup.main_controller" elementType="LoopController" guiclass="LoopControlPanel" testclass="LoopController">
          <boolProp name="LoopController.continue_forever">true</boolProp>
          <stringProp name="LoopController.loops">-1</stringProp>
        </elementProp>
        <stringProp name="ThreadGroup.num_threads">{threads}</stringProp>
        <stringProp name="ThreadGroup.ramp_time">5</stringProp>
        <boolProp name="ThreadGroup.scheduler">true</boolProp>
        <stringProp name="ThreadGroup.duration">{duration}</stringProp>
        <stringProp name="ThreadGroup.delay">0</stringProp>
      </ThreadGroup>
      <hashTree>
{csv}
        <HeaderManager guiclass="HeaderPanel" testclass="HeaderManager" testname="headers">
          <collectionProp name="HeaderManager.headers">
{headers}
          </collectionProp>
        </HeaderManager>
        <hashTree/>
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="{name}">
          <stringProp name="HTTPSampler.domain">127.0.0.1</stringProp>
          <stringProp name="HTTPSampler.port">8090</stringProp>
          <stringProp name="HTTPSampler.protocol">http</stringProp>
          <stringProp name="HTTPSampler.path">{path}</stringProp>
          <stringProp name="HTTPSampler.method">{method}</stringProp>
          <boolProp name="HTTPSampler.follow_redirects">true</boolProp>
          <boolProp name="HTTPSampler.use_keepalive">true</boolProp>
          <boolProp name="HTTPSampler.postBodyRaw">{raw}</boolProp>
          <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
            <collectionProp name="Arguments.arguments">
{body}
            </collectionProp>
          </elementProp>
        </HTTPSamplerProxy>
        <hashTree/>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""

CSV_BLOCK = """        <CSVDataSet guiclass="TestBeanGUI" testclass="CSVDataSet" testname="users">
          <stringProp name="filename">/tmp/perf/users.csv</stringProp>
          <stringProp name="fileEncoding">UTF-8</stringProp>
          <stringProp name="variableNames">username,password,token</stringProp>
          <boolProp name="ignoreFirstLine">true</boolProp>
          <stringProp name="delimiter">,</stringProp>
          <boolProp name="quotedData">false</boolProp>
          <boolProp name="recycle">true</boolProp>
          <boolProp name="stopThread">false</boolProp>
          <stringProp name="shareMode">shareMode.all</stringProp>
        </CSVDataSet>
        <hashTree/>"""

HEADER = """            <elementProp name="{n}" elementType="Header">
              <stringProp name="Header.name">{n}</stringProp>
              <stringProp name="Header.value">{v}</stringProp>
            </elementProp>"""

BODY = """              <elementProp name="" elementType="HTTPArgument">
                <boolProp name="HTTPArgument.always_encode">false</boolProp>
                <stringProp name="Argument.value">{v}</stringProp>
                <stringProp name="Argument.metadata">=</stringProp>
              </elementProp>"""


def gen(name, method, path, threads, duration, headers=None, body=None, csv=False):
    headers = headers or []
    hdrs = "\n".join(HEADER.format(n=k, v=v) for k, v in headers)
    if body:
        b = BODY.format(v=body)
        raw = "true"
    else:
        b = ""
        raw = "false"
    return TPL.format(
        name=name, threads=threads, duration=duration, path=path, method=method,
        headers=hdrs, body=b, raw=raw, csv=(CSV_BLOCK if csv else ""),
    )


if __name__ == "__main__":
    scenario, threads, duration = sys.argv[1], sys.argv[2], sys.argv[3]
    if scenario == "hot":
        xml = gen("hot_feed", "GET", "/api/feed/hot?limit=10", threads, duration)
    elif scenario == "latest":
        xml = gen("latest_feed", "GET", "/api/feed/latest?limit=10", threads, duration)
    elif scenario == "login":
        xml = gen("login", "POST", "/api/auth/login", threads, duration,
                  headers=[("Content-Type", "application/json")],
                  body='{"username":"${username}","password":"${password}"}', csv=True)
    elif scenario == "like":
        post_id = open("/tmp/perf/target.txt").read().strip()
        xml = gen("like", "POST", f"/api/posts/{post_id}/like", threads, duration,
                  headers=[("Content-Type", "application/json"),
                           ("Authorization", "Bearer ${token}")], csv=True)
    else:
        raise SystemExit("unknown scenario")
    print(xml)
