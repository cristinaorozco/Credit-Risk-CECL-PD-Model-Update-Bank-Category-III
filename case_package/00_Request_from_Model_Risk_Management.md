**From:** Model Risk Management, Consumer Credit
**To:** Optimum Quants LLC
**Subject:** Consumer CECL PD model: monitoring alert, please assess and propose

Hello,

Our quarterly monitoring for the consumer CECL model came back worse than expected. The summary is in `monitoring_pack/`: actual defaults are above what the model predicted in most pools, and the macro inputs moved. We would like your help to understand it and to decide what to do.

**What we need from you**
1. Assess whether the production model needs to change, and what kind of change it is (see our policy excerpt in `02_Model_Change_Policy_Excerpt.md`).
2. If it does, carry the change out on the attached data, quantify the impact on expected loss and validate the result.
3. Send us the documents we need for governance: change request, technical report, updated monitoring plan, and a fair-lending follow-up.

**What we send**
* `data/raw/`: loan-level extracts for the development and the monitoring periods, as pulled from the loan system. We have not cleaned them.
* `01_Model_Documentation_v1.md` and `data/production_model/`: model summary and the PD, LGD and EAD tables in production.
* `monitoring_pack/`: latest monitoring results and the monitoring plan in force.
* `02_Model_Change_Policy_Excerpt.md`: model change policy excerpt.

**Points to know**
* We are a Category III institution.
* The data owner could not confirm every field; please document any assumption you make.
* Please tell us if anything in the package is missing or inconsistent.

Thank you.
