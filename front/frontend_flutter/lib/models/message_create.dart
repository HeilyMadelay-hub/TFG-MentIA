class MessageCreate {
  final String question;
  final List<int>? documentIds;
  final int? nResults;

  MessageCreate({
    required this.question,
    this.documentIds,
    this.nResults,
  });

  Map<String, dynamic> toJson() {
    final Map<String, dynamic> json = {
      'question': question,
    };

    if (documentIds != null && documentIds!.isNotEmpty) {
      json['document_ids'] = documentIds;
    }

    if (nResults != null) {
      json['n_results'] = nResults;
    }

    return json;
  }
}
