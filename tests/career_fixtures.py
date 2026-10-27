"""Fictional cross-discipline cases; no real career data."""

CASES = {
    'hiring': ('Talent and hiring', 'Hiring operations', 'Interview calibration', 'ATS',
               'I introduced a shared scorecard after interviewers used different criteria.',
               'The panel used the scorecard for the next search. Hiring speed was not measured.',
               'Hiring managers defined the technical criteria.', 'No measured time-to-hire improvement.', 'scorecard'),
    'engineering': ('Engineering', 'Platform engineering', 'Safer queue retries', 'Git repository',
                    'I implemented idempotency keys and a retry limit after duplicate jobs appeared in staging.',
                    'Tests passed and the change merged. Production adoption is not documented.',
                    'Contributor 02 designed the queue; Contributor 03 reviewed the fix.', 'No production reliability measurement.', 'architecture'),
    'operations': ('Operations', 'Business operations', 'Request ownership', 'Document export',
                   'I mapped request handoffs and added an exception owner to the weekly review.',
                   'The team used the review for two recorded weeks. No cycle-time baseline exists.',
                   'Team leads owned the operating decisions.', 'Continued use beyond two weeks is unknown.', 'workflow'),
    'growth': ('Growth', 'Growth experiments', 'Activation experiment', 'Analytics export',
               'I proposed a shorter onboarding flow and defined activation before the test.',
               'The export records 12 activations from 40 treatment users and 8 from 40 control users.',
               'Engineering implemented the flow; analytics checked the event definitions.', 'Small sample; no causal or durable lift established.', 'experiment'),
    'marketing': ('Marketing', 'Product marketing', 'Launch message study', 'Campaign files',
                  'I wrote the launch brief and two message variants for the product page.',
                  'The page launched with the revised message. Revenue attribution is unavailable.',
                  'Design produced the creative; the product team reviewed accuracy.', 'Launch is not evidence of increased revenue.', 'creative'),
    'bd': ('Business development', 'Partnerships', 'Partner onboarding pilot', 'CRM export',
           'I qualified the partner need and drafted the pilot scope with the partner team.',
           'The pilot agreement was signed. Implementation and realized revenue are not recorded.',
           'Legal negotiated terms; the integration team owns delivery.', 'Signed pipeline is not booked or realized revenue.', 'partner-map'),
}


def context(role):
    discipline, target, title, platform, contribution, outcome, credit, limit, tag = CASES[role]
    return {'schema': 'career-context/v1', 'synthetic': True, 'updatedAt': '2030-09-01', 'reviewStatus': 'draft',
            'person': {'name': 'Contributor 01', 'overview': f'Selected {discipline.lower()} work, with a focus on {target.lower()}.', 'background': []},
            'profile': {'disciplines': [discipline], 'targetRoles': [target], 'emphasis': [tag],
                        'referenceNotes': 'Use selected work first; employment dates are not supplied.'},
            'collection': [{'platform': platform, 'location': 'Selected fictional project', 'access': 'supplied',
                            'status': 'partial', 'scope': 'One supplied project note; dates not supplied. Original attachments unavailable.',
                            'nextStep': 'Inspect a selected original if the person supplies it.'}],
            'accounts': [{'id': role, 'title': title, 'period': 'Project dates not supplied', 'summary': contribution + ' ' + outcome,
                          'context': 'The selected project note records a shared team initiative.', 'aim': title,
                          'contribution': contribution, 'decisions': [contribution], 'sharedCredit': credit, 'outcome': outcome,
                          'limits': [limit], 'questions': [], 'sourceRefs': [role + '-note'], 'tags': [tag]}],
            'sources': [{'id': role + '-note', 'label': 'Supplied project note', 'kind': 'person_account',
                         'content': contribution + ' ' + outcome + ' ' + credit + ' ' + limit,
                         'scope': 'Fictional self-report for workflow tests; not independent verification.'}]}


def resume(packet, fingerprint):
    account = packet['accounts'][0]
    return {'schema': 'resume-draft/v1', 'contextSha256': fingerprint, 'preparedOn': '2030-09-01',
            'target': packet['profile']['targetRoles'][0], 'referenceNotes': packet['profile']['referenceNotes'],
            'summary': None, 'sections': [{'title': 'Selected projects', 'entries': [{
                'heading': account['title'], 'details': '', 'accountIds': [account['id']],
                'bullets': [account['contribution'] + ' ' + account['sharedCredit'],
                            account['outcome'] + ' ' + account['limits'][0]]}]}]}
