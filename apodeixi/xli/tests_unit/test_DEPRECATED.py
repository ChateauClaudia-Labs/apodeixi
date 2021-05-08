import sys                              as _sys
import datetime
import pandas                           as pd
import yaml                             as _yaml

from apodeixi.xli.DEPRECATED            import BreakdownBuilder, L1L2_Link
from apodeixi.xli                       import UID_Store
from apodeixi.util.a6i_unit_test     import ApodeixiUnitTest
from apodeixi.util.a6i_error        import ApodeixiError, FunctionalTrace

class Test_MultiSheet(ApodeixiUnitTest): 
    '''
    Tests the BreakdownBuilder's ability to assemble a tree out of multiple worksheets: 1 'master' worksheet
    for Level1 and then for each Level1 node, a worksheet spelling out Level2/Level3 
    '''
    def setUp(self):
        super().setUp()

        _PRODUCT                = 'product'
        _JOURNEY                = 'journey'
        _PLAN_TYPE              = 'planType'
        _SCENARIO               = 'scenario'
        _ENVIRONMENT            = 'environment'
        _SCORING_CYCLE          = 'scoringCycle'
        _SCORING_MATURITY       = 'scoringMaturity'
        _ESTIMATED_BY           = 'estimatedBy'
        _ESTIMATED_ON           = 'estimatedOn'
        _RECORDED_BY            = 'recordedBy'
        _PURSUIT                = 'pursuit'
        _BREAKDOWN_TYPE         = 'breakdownType'
        CTX                      = {}
        CTX[_PURSUIT]            = 'test_multi_sheet_pursuit'
        CTX[_SCENARIO]           = 'Baseline'
        CTX[_ENVIRONMENT]        = 'Production'
        CTX[_SCORING_CYCLE]      = 'FY22'
        CTX[_SCORING_MATURITY]   = 'Draft'
        #CTX[_ESTIMATED_BY]       = 'a'
        CTX[_ESTIMATED_ON]       =  datetime.datetime.strptime('2021-04-27', '%Y-%m-%d')
        CTX[_RECORDED_BY]        = 'alejandro.hernandez@finastra.com'
        CTX[_BREAKDOWN_TYPE]     = 'Opus cloud initiative'
        
        self.CTX                 = CTX
        

    def test_multi_sheet(self):


        #EXCEL_POSTINGS_FOLDER  = _os.getcwd() + '/../test-repos/' + 'excel-postings' # Run at root project level
        EXCEL_POSTINGS_FOLDER  = self.input_data 

        EXPECTATIONS_FILE      = 'test_multi_sheet_input.xlsx'
        EXPECTATIONS_RANGE     = 'a4:e100'
        SHEETS                 = ['Ew' + str(idx) for idx in range(10)]   
        
        MANIFESTS_REPO         = self.output_data #_os.getcwd() + '/../test-repos/' + 'manifests-repo' # Run at root project level
        L0_SHEET               = "Generated"
        l0_url                 = EXCEL_POSTINGS_FOLDER + '/' + EXPECTATIONS_FILE + ':' + L0_SHEET
        l0_range               = "A1:G30"        
        level1                 = ['W' + str(idx) for idx in range(len(SHEETS))]    
        
        L1_ids                 = ['W' + str(idx) for idx in range(len(SHEETS))]
        store                  = UID_Store()
        store.initialize(L1_ids)
        LINKS                  = []
        for idx in range(len(SHEETS)):
            #uid      = store.generateUID(acronym='W', parent_UID=None)
            #L1_ids.append(uid)
            LINKS.append(L1L2_Link(L1_UID         = level1[idx], \
                                   L2_URL         = EXCEL_POSTINGS_FOLDER + '/' + EXPECTATIONS_FILE + ':' + SHEETS[idx], \
                                   L2_excel_range = EXPECTATIONS_RANGE))  
         
        result = ''
        try:
            builder = BreakdownBuilder(ctx=self.CTX, links=LINKS, l0_url=l0_url, l0_excel_range=l0_range, \
                                       manifests_repo_dir=MANIFESTS_REPO, uid_store=store)
            result = builder.build()            
        except ValueError as ex:
            result = ex
        self.assertEqual(result, self._expected())
            
    def _expected(self):
        return 'apiVersion: breakdown.a6i.io/v1dev\nbreakdown:\n  defined_by: alejandro.hernandez@finastra.com\n  defined_on: 2021-04-27 00:00:00\n  streams:\n    W0: Cloud value proposition\n    W0-detail:\n      Description: Define value proposition for customers on the Cloud\n      Lead: "Product Strategy \\u2013 Mike S"\n      P metric: TBD\n      R metric: TBD\n      Support: Andrei\n      UID: W0\n      expectations:\n        E1: Analyze segmentation\n        E1-detail:\n          UID: W0.E1\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W0.E1.A1\n              description: \'Segmentation tree: consolidated tree of segments (verticals,\n                geos, tiers, and breakouts for either) \'\n            A2:\n              UID: W0.E1.A2\n              description: Size at each leaf in the segmentation tree\n            A3:\n              UID: W0.E1.A3\n              description: Quantification of how much of that could be cloud\n          description: Break Finastra\'s space into segments and for each measure the\n            appetite for cloud\n        E2: Analyze "Jobs to be done" / Personas\n        E2-detail:\n          UID: W0.E2\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W0.E2.A1\n              description: Narrated diagrams indicating the timeline-based tasks that\n                Personas engage with and where the struggle lies, using standard notations\n                such as BPMN flows or UML sequence diagrams.\n          description: Using Design Thinking and Clayton Christensens "Jobs to be\n            done" methodology, for each cloud-friendly segment describe the personas\n            and what "struggle" (as in Christensen\'s approach) they are in.\n        E3: Define Value propositions\n        E3-detail:\n          UID: W0.E3\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W0.E3.A1\n              description: Vision Statement for Value Proposition, using the FOR/WHO/THE/THAT/UNLIKE/OUR\n                PRODUCT template from Geoffrey Moore\n            A2:\n              UID: W0.E3.A2\n              description: Logical diagram of capabilities\n            A3:\n              UID: W0.E3.A3\n              description: Mapping to the Finastra products that would provide such\n                capabilities\n            A4:\n              UID: W0.E3.A4\n              description: Mapping to the "Jobs to be done" diagrams with a narration\n                on how the capabilities in question address the "struggle"\n          description: Define logical bundle of Finastra capabilities which would\n            address each of the "jobs to be done" for each of the cloud-friendly struggles.\n            May be from a Finastra product or a combination of Finastra products.\n        E4: Measure Opportunities\'s size\n        E4-detail:\n          UID: W0.E4\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W0.E4.A1\n              description: Revenue projection per proposition expressed as a table\n                (time vs revenue)\n          description: For each of the value propositions, establish a revenue projection\n            timeline over the next 3 years assuming that Finastra chooses to get into\n            that space\n        E5: Decide areas to prioritize\n        E5-detail:\n          UID: W0.E5\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W0.E5.A1\n              description: A decision-making model to choose the propositions with\n                the highest ROI\n          description: Determine the priorities to which investment should be focused\n        E6: Fail Fast\n        E6-detail:\n          UID: W0.E6\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W0.E6.A1\n              description: Updated artifacts for segmentation, "jobs to be done"/personas,  value\n                props, opportunity sizing, and prioritization\n          description: Adjust analysis and value propositions as new data comes in,\n            specially around success (or failure) of first market launches\n    W1: Modernization\n    W1-detail:\n      Description: \'Deliver the main components of the cloud roadmap: Microservices,\n        Containerization, Multi-tenancy, UX, Operations / DevOps\'\n      Lead: Alex\n      P metric: \'# of EPICs delivered in time and budgetExample: By Aug: 20%(20% of\n        what is expected in the 12 months of FY 22 has been done)\'\n      R metric: \'Product [X] to target state [Y] by time [Z]Example: Product: Essence\n        to Webapp by end of FY22.\'\n      Support: Leigh, GMs, Ouafa\n      UID: W1\n      expectations:\n        E1: Finishing line\n        E1-detail:\n          UID: W1.E1\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W1.E1.A1\n              description: List of Value Propositions in scope for product\n            A2:\n              UID: W1.E1.A2\n              description: \'Numerical business outcome KPIs and targets. Typically:\n                size of CAM expansion, quantification of margin improvements and of\n                any new forms of revenue (for example, perhaps from selling to lower\n                tiers)\'\n            A3:\n              UID: W1.E1.A3\n              description: \'Numerical technical KPIs and targets needed to meet business\n                outcome KPIs. Typically: cost-per-tenant, TTM, Quality, QoS, etc.\'\n          description: Description of measurable conditions that, if true, indicate\n            that the modernization journey is over because it met its goals.\n        E2: Define architecture target\n        E2-detail:\n          UID: W1.E2\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W1.E2.A1\n              description: Target-state deployment diagrams\n            A2:\n              UID: W1.E2.A2\n              description: Target-state reliabiliy model\n            A3:\n              UID: W1.E2.A3\n              description: For each KPI, a model to predict what the KPI value would\n                be in the target state architecure\n          description: Blueprint for a target state architecture that, if achieved,\n            would deliver the technical KPI targets.\n        E3: Define operational target\n        E3-detail:\n          UID: W1.E3\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W1.E3.A1\n              description: Target-state service operating model\n            A2:\n              UID: W1.E3.A2\n              description: Cost model for target state service operating model\n            A3:\n              UID: W1.E3.A3\n              description: For each KPI of an operational nature, a model to predict\n                what its value would be in the target state operating model.\n          description: Model for how product will be operated in the target state\n        E4: Define milestones for journey\n        E4-detail:\n          UID: W1.E4\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W1.E4.A1\n              description: Enumeration of milestones and when in time they happen\n            A2:\n              UID: W1.E4.A2\n              description: For each milestone, a mapping to a Value Proposition (or\n                portion thereof) that is enabld by the milestone\n            A3:\n              UID: W1.E4.A3\n              description: \'For each milestone, quantified identification of what\n                business outcome KPIs it enables. Typically: size of CAM expansion,\n                margin improvements, new forms of revenue it enables.\'\n          description: Decomposition of modernization journey into "milestones", where\n            each milestone has an identifiable customer-facing value and can be monetized\n        E5: Commit roadmap\n        E5-detail:\n          UID: W1.E5\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W1.E5.A1\n              description: Mapping of Aha epics to the milestones\n            A2:\n              UID: W1.E5.A2\n              description: Mapping of roadmap to modernization tactics\n          description: Enumeration of Aha epics over next 4-6 quarters, with a mapping\n            to the milestone(s) they enable\n        E6: Commit investment\n        E6-detail:\n          UID: W1.E6\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W1.E6.A1\n              description: Timeline of how many man-days are committed to modernization\n                for each of the next fiscal years, up to the moment when modernization\n                is done.\n          description: Projection in time on the amount of investment for the modernization\n            journey\n        E7: Deliver modernization\n        E7-detail:\n          UID: W1.E7\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W1.E7.A1\n              description: Burnout of Aha epics corresponding to milestones\n            A2:\n              UID: W1.E7.A2\n              description: Delivery of milestones adhering to the EA standards for\n                each of the modernization tactics\n          description: Timely on-budget delivery of subsequent milestones until the\n            journey is complete, adhering to EA standards\n    W2: Software delivery and production operations\n    W2-detail:\n      Description: \'FusionOperate: Increase automation through deployment and DevOps\n        across all cloud propositions (FMS, FusionCloud, etc). Support native cloud\n        at scale\'\n      Lead: Leigh\n      P metric: \'% automated tests integrated with pipeline\'\n      R metric: \'% Cloud clients compliant with EA operating standards & policy (measured\n        quarterly)\'\n      Support: Russ, Bryan, Ouafa, Andrew\n      UID: W2\n      expectations:\n        E1: Definition of EA Operating Standards\n        E1-detail:\n          UID: W2.E1\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W2.E1.A1\n              description: CI/CD(GitOps) standards\n            A2:\n              UID: W2.E1.A2\n              description: Reliability standards\n            A3:\n              UID: W2.E1.A3\n              description: Monitoring standards\n            A4:\n              UID: W2.E1.A4\n              description: Testing standards\n            A5:\n              UID: W2.E1.A5\n              description: Security standars\n          description: Define the EA Operating Standards that must be complied with\n            for products going to cloud\n        E2: Define how all cloud propositions can be supported with FusionOperate\n        E2-detail:\n          UID: W2.E2\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W2.E2.A1\n              description: "Define FusionCloud (SaaS) SOM via FusionOperate: \\n*full\\\n                \\ CI/CD automation; \\n*multi*tenant environments; \\n*multi*tenant\\\n                \\ ops (monitoring, upgrades, \\u2026)\\n*no customizations; \\n*n-1"\n            A2:\n              UID: W2.E2.A2\n              description: "Define Cloud@Scale SOM via FusionOperate: \\n*full CI/CD\\\n                \\ automation; \\n*single*tenant customer environments; \\n*multi*tenant\\\n                \\ ops (monitoring, upgrades, \\u2026)\\n*no customizations; \\n*n-1"\n            A3:\n              UID: W2.E2.A3\n              description: "Define FMS SOM via FusionOperate: \\n*full CI/CD automation;\\\n                \\ \\n*single*tenant customer environments; \\n*single*tenant ops (monitoring,\\\n                \\ upgrades, \\u2026)\\n*customizations built via FO\'s software factory\\\n                \\ and FFDC APIs\\n*n-3 or better"\n            A4:\n              UID: W2.E2.A4\n              description: Define partner-hosted SOMs by reference to the Finastra-hosted\n                SOMs (FusionCloud, Cloud@Scale, FMS)\n          description: Define all operating models and how FusionOperate is used in\n            each of them\n        E3: Define FusionOperate technical value proposition\n        E3-detail:\n          UID: W2.E3\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W2.E3.A1\n              description: Architecture blueprint for Software Factory\n            A2:\n              UID: W2.E3.A2\n              description: Architecture blueprint for Operating Platform\n            A3:\n              UID: W2.E3.A3\n              description: Architecture blueprint for Testing Platform\n            A4:\n              UID: W2.E3.A4\n              description: Architecture blueprint for Monitoring Platform\n          description: Define the scope of FusionOperate capabilities in a way that\n            it addresses all cross-cutting concerns across Finastra products going\n            to cloud, so that they are addressed once, across the whole DevSecOps\n            spectrum (CI/CD, reliability model, security model, etc.)\n        E4: Deliver FusionOperate\n        E4-detail:\n          UID: W2.E4\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W2.E4.A1\n              description: \'Developer productivity KPIs set and met \'\n            A2:\n              UID: W2.E4.A2\n              description: Customer onboarding KPIs set and met. KPIs targets must\n                relate to the modernization stream\'s business outcome KPIs.\n            A3:\n              UID: W2.E4.A3\n              description: Cost-of-operation KPIs set and met. KPIs targets must relate\n                to the modernization stream\'s business outcome KPIs.\n            A4:\n              UID: W2.E4.A4\n              description: Speed-of-upgrades KPIs set and met. KPIs targets must relate\n                to the modernization stream\'s business outcome KPIs.\n          description: Deliver a Finastra-wide DevSecOps platform based on SDNs, K8s\n            and GitOps\n    W3: N-1 compliance (excl. FMS)\n    W3-detail:\n      Description: \'Institutionalise a release and sales policy to ensure all hosted\n        customers are on the latest GA release \'\n      Lead: Michael M\n      P metric: \'% of Finastra client contracts signed with N-1 compliance clause\'\n      R metric: \'% of Finastra-hosted clients post Feb 1st, 2021 implemented and maintained\n        on N-1 version\'\n      Support: GMs, Andrew\n      UID: W3\n      expectations:\n        E1: Update commercial policy\n        E1-detail:\n          UID: W3.E1\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W3.E1.A1\n              description: Updated commercial policy for all cloud SOMs except FMS\n          description: Update commercial policy to ensure that sales contracts empower\n            Finastra to enforce n-1 (except for FMS)\n        E2: Engage in Opportunities desk\n        E2-detail:\n          UID: W3.E2\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W3.E2.A1\n              description: Periodic report on opportunities and the SOM they were\n                directed to\n          description: Engage in the cloud sales opportunities desks to steer as many\n            opportunities as possible towards the operating models that ensure n-1\n            (Cloud@Scale, FusionCloud)\n        E3: Alert on any n-1 degradation\n        E3-detail:\n          UID: W3.E3\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W3.E3.A1\n              description: Periodic report on customer environments that are on Cloud@Scale\n                or FusionCloud and flagging any n-1 violation\n          description: For cloud sales steered towards SOMs that ensure n-1 (Cloud@Scale,\n            FusionCloud), monitor the customer environments on a permanent basis to\n            ensure that as new product releases occur, the n-1 constraint is enforced\n            (i.e., those environments get upgraded)\n    W4: FMS / AMS\n    W4-detail:\n      Description: Develop and implement a 3-year conversion programme to accelerate\n        sales of Fusion Managed Services solutions for LoanIQ, Trade Innovation, GPP\n        and Kondor\n      Lead: Andrew\n      P metric: FMS SW pipeline of [$XM]\n      R metric: FMS accretive SW bookings of [$XM]\n      Support: Neil\n      UID: W4\n      expectations:\n        E1: Adopt FFDC as exclusive SDK for all customizations\n        E1-detail:\n          UID: W4.E1\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W4.E1.A1\n              description: .nan\n          description: \'\'\n        E2: Adopt of Fusion Operate as only delivery mechanism\n        E2-detail:\n          UID: W4.E2\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W4.E2.A1\n              description: Customizations built with FO\'s Software Factory\n            A2:\n              UID: W4.E2.A2\n              description: Full CI/CD automation, with GitOps\n            A3:\n              UID: W4.E2.A3\n              description: Adoption of FO\'s Monitoring Platform - logs and traces\n                done consistently\n            A4:\n              UID: W4.E2.A4\n              description: Networking via FO\'s FusionDelivery (SDN)\n            A5:\n              UID: W4.E2.A5\n              description: G/S developers to provide AppOps for the customizations\n                they write\n          description: \'\'\n        E3: Manage margins and cost structure\n        E3-detail:\n          UID: W4.E3\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W4.E3.A1\n              description: .nan\n            A2:\n              UID: W4.E3.A2\n              description: .nan\n          description: \'\'\n        E4: Align sales pipeline with Value Propositions\n        E4-detail:\n          UID: W4.E4\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W4.E4.A1\n              description: .nan\n          description: Focus on preparing GTMs for the value propositions identified\n            and prioritized in workstream W0\n    W5: Cloud sales (excl. FMS)\n    W5-detail:\n      Description: Develop and implement GTM and deal support across the sales cycle\n        to accelerate Cloud sales. Scope includes collateral, materials, references,\n        SPP build outs and alignment of product readiness with the messaging / GTM\n        process\n      Lead: Hannes\n      P metric: Cloud pipeline by product by region of [$XM]\n      R metric: Cloud bookings of [$XM]\n      Support: Rudy\n      UID: W5\n      expectations:\n        E1: Align sales pipeline with Value Propositions\n        E1-detail:\n          UID: W5.E1\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W5.E1.A1\n              description: .nan\n          description: Focus on preparing GTMs for the value propositions identified\n            and prioritized in workstream W0\n    W6: Pricing\n    W6-detail:\n      Description: Develop and implement pricing approach for Cloud to ensure pricing\n        takes full account of costs (infrastructure) and workload (e.g., Level 1 support)\n        is moved from client to Finastra when move from on prem to cloud\n      Lead: Christian\n      P metric: Delivery of milestones per product\n      R metric: Pricing approach developed and implemented for all Cloud products\n      Support: Brad B., Bruce B.\n      UID: W6\n      expectations:\n        E1: Align packaging with Value Propositions\n        E1-detail:\n          UID: W6.E1\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W6.E1.A1\n              description: \'Possible bundling models for each value prop, along dimensions\n                like:\n\n                * What is licensed separately\n\n                * What is sold via partners, under a variety of scenarios (white label,\n                OEM, etc.)\'\n            A2:\n              UID: W6.E1.A2\n              description: \'For each bundling model, analyze monetization potential\n                by identifying what fees can be commanded given the segmentation sizing\n                analysis from stream W0\n\n                * Upfront fees\n\n                * Usage fees\n\n                * Support fees\n\n                * Renewal fees\n\n                * Partner fees\n\n                etc.\'\n          description: Define  packaging associated to the prioritized value propositions\n            from workstream W0\n        E2: Define pricing\n        E2-detail:\n          UID: W6.E2\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W6.E2.A1\n              description: Definition of packages (as bundles) and the pricing structure  for\n                each.\n            A2:\n              UID: W6.E2.A2\n              description: .nan\n            A3:\n              UID: W6.E2.A3\n              description: .nan\n          description: From analysis of bundling models and monetization models, determine\n            the package(s) and associated fees that will be taken to market\n        E3: Ensure profitability\n        E3-detail:\n          UID: W6.E3\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W6.E3.A1\n              description: .nan\n          description: Identify the full cost for the packaging in question, and ensure\n            that price is set so that a target margin can result\n    W7: IT role in native Cloud solutions\n    W7-detail:\n      Description: Revamp, rework and modernize network and infrastructure to support\n        cloud at scale. Scope will address network support to deliver and deploy at\n        scale, end to end monitoring and extensive automation\n      Lead: Russ\n      P metric: \'% network deployment automated% products onboarded to status page\'\n      R metric: \'[X%] Cloud clients compliant utilizing modern network connectivity\'\n      Support: Leigh, Bryan\n      UID: W7\n      expectations:\n        E1: Align with Fusion Operate\n        E1-detail:\n          UID: W7.E1\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W7.E1.A1\n              description: .nan\n          description: Understand the FusionOperate strategy around cloud-native networking,\n            service mesh, Fusion Delivery and GitOps, to focus on areas where IT\'s\n            support is needed, and avoid duplication by not involving IT into areas\n            that FO plans to take care of.\n    W8: Customer Support for native Cloud solutions\n    W8-detail:\n      Description: Implement Cloud customer support model across DevOps, IT and customer\n        support\n      Lead: \'Michael \'\n      P metric: Delivery of milestones per product\n      R metric: Number of products with customer self-service capabilities supportability\n        embedded made available to customers\n      Support: Leigh\n      UID: W8\n      expectations:\n        E1: Align with Fusion Operate\n        E1-detail:\n          UID: W8.E1\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W8.E1.A1\n              description: .nan\n          description: Define how customer support would work for each of the service\n            operating models that rely on Fusion Operate (FusionCloud, Cloud@Scale,\n            FMS, and partner-hosted)\n    W9: Talent transformation\n    W9-detail:\n      Description: \'Define and deliver skills & capabilities required fordelivering\n        Cloud faster across organization: Product, GCO, CCO.\'\n      Lead: Clare\n      P metric: "Skills & capabilities plans completed\\u200B (by workstream)"\n      R metric: Actions from plans in place (training, hires, capabilities addressed)\n      Support: Shira, Neeha\n      UID: W9\n      expectations:\n        E1: Launch FusionOperate - oriented training\n        E1-detail:\n          UID: W9.E1\n          acceptance-criteria-artifacts:\n            A1:\n              UID: W9.E1.A1\n              description: Launch OpenShift training\n            A2:\n              UID: W9.E1.A2\n              description: Launch K8S/SDN-based Networking training\n            A3:\n              UID: W9.E1.A3\n              description: Launch GitOps training\n            A4:\n              UID: W9.E1.A4\n              description: Launch AppOps training\n            A5:\n              UID: W9.E1.A5\n              description: Launch Terraform training\n          description: Devise and launch training programs in the technologies that\n            development teams need in order to leverage the self-service capabilities\n            in FusionOperate and take ownership of their production deliveries\n  type: Opus cloud initiative\nkind: Breakdown\nmetadata:\n  labels:\n    pursuit: test_multi_sheet_pursuit\n    scenario: Baseline\n    scoringCycle: FY22\n  name: test_multi_sheet_pursuit.Baseline\n  namespace: Production.FY22\nplanMaturity: Draft\n'


if __name__ == "__main__":
    # execute only if run as a script
    def main(args):
        T = Test_MultiSheet()
        T.setUp()
        what_to_do = args[1]
        if what_to_do=='multi_sheet':
            T.test_multi_sheet()

    main(_sys.argv)