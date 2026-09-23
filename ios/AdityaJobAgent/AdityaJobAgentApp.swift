import SwiftUI

struct Job: Codable, Identifiable {
    let id: String
    let source: String
    let company: String
    let title: String
    let location: String
    let url: String
    let description: String
    let posted_at: String
    let matched_skills: [String]
    let score: Int
    let first_seen: String
}

@MainActor
final class JobStore: ObservableObject {
    @Published var jobs: [Job] = []
    @Published var loading = false
    @Published var error: String?

    private let feedURL = URL(string:
        "https://raw.githubusercontent.com/moodyadi/ai-career-agent/main/data/jobs.json"
    )!

    func refresh() async {
        loading = true
        defer { loading = false }
        do {
            let (data, _) = try await URLSession.shared.data(from: feedURL)
            jobs = try JSONDecoder().decode([Job].self, from: data)
                .sorted { $0.score > $1.score }
            error = nil
        } catch {
            error = error.localizedDescription
        }
    }
}

@main
struct AdityaJobAgentApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

struct ContentView: View {
    @StateObject private var store = JobStore()

    var body: some View {
        NavigationStack {
            List(store.jobs) { job in
                NavigationLink {
                    JobDetail(job: job)
                } label: {
                    VStack(alignment: .leading, spacing: 5) {
                        Text(job.title).font(.headline)
                        Text(job.company).foregroundStyle(.secondary)
                        Text("\(job.location) • Match \(job.score)%")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("Job Radar")
            .refreshable { await store.refresh() }
            .overlay {
                if store.loading && store.jobs.isEmpty {
                    ProgressView()
                } else if let error = store.error, store.jobs.isEmpty {
                    ContentUnavailableView("Could not load jobs",
                                           systemImage: "wifi.exclamationmark",
                                           description: Text(error))
                } else if store.jobs.isEmpty {
                    ContentUnavailableView("No jobs yet",
                                           systemImage: "briefcase",
                                           description: Text("Pull to refresh."))
                }
            }
            .task { await store.refresh() }
        }
    }
}

struct JobDetail: View {
    let job: Job

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(job.title).font(.title2).bold()
                Text(job.company).font(.headline)
                Text("Match: \(job.score)%")
                    .font(.headline)
                if !job.matched_skills.isEmpty {
                    Text("Matched skills")
                        .font(.headline)
                    Text(job.matched_skills.joined(separator: ", "))
                        .foregroundStyle(.secondary)
                }
                Text(job.description)
                    .textSelection(.enabled)

                if let url = URL(string: job.url) {
                    Link("Open application", destination: url)
                        .buttonStyle(.borderedProminent)
                }
            }
            .padding()
        }
        .navigationTitle("Job")
        .navigationBarTitleDisplayMode(.inline)
    }
}
