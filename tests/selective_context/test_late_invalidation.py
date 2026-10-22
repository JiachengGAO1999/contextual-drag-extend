from selective_context.late_invalidation import gate0, gate1


def fixture():
    qs = [dict(id=str(i),cohort="confirmation") for i in range(96)]
    data = []
    for q in qs:
        for w in ("note","sentence"):
            for order in (0,1):
                for condition, p in (("PRE",.8),("POST",.6),("PLACEBO_PRE",.7),("PLACEBO_POST",.5)):
                    data.append(dict(id=q["id"],wording=w,order=order,condition=condition,
                        revision=0,p_correct=p,option_mass=.8))
    return dict(independent=qs),data


def test_placebo_position_effect_cannot_pass_as_specific_invalidation_effect():
    m,data=fixture()
    result=gate1(m,data,0,"confirmation")
    assert result["raw_pre_minus_post"]["mean"] > .19
    assert abs(result["corrected_pre_minus_post"]["mean"]) < 1e-9
    assert not result["passed"]


def test_question_is_unit_and_missing_order_removes_only_that_pair():
    m,data=fixture()
    for r in data:
        if r["condition"] == "PLACEBO_PRE":
            r["p_correct"] = .5
    result=gate1(m,data,0,"confirmation")
    assert result["passed"]
    assert result["corrected_pre_minus_post"]["n"] == 96
    missing=[r for r in data if not(r["id"]=="0" and r["order"]==1)]
    result=gate1(m,missing,0,"confirmation")
    assert result["corrected_pre_minus_post"]["n"] == 95
    assert result["missing"] == ["0"]


def test_conditional_preference_without_candidate_probability_mass_fails_calibration():
    q=dict(id="q",cohort="discovery")
    m=dict(calibration=[q],independent=[q])
    data=[dict(id="q",condition=c,order=o,wording="note",revision=0,
               p_correct=p,option_mass=.0001)
          for c,p in (("CLEAN",.9),("POST",.5)) for o in (0,1)]
    assert not gate0(m,data,0)["passed"]
