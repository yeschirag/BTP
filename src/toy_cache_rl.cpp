#include <bits/stdc++.h>
using namespace std;

constexpr int WAYS = 8;
constexpr int KEEP = 0;
constexpr int EVICT = 1;

/* ===================== Cache ===================== */

struct CacheLine {
    bool valid = false;
    uint64_t tag = 0;
};

class ToyCache {
public:
    vector<CacheLine> lines;
    deque<int> lru; // front = MRU, back = LRU

    ToyCache() {
        lines.resize(WAYS);
        for (int i = 0; i < WAYS; i++)
            lru.push_back(i);
    }

    int find(uint64_t tag) {
        for (int i = 0; i < WAYS; i++) {
            if (lines[i].valid && lines[i].tag == tag)
                return i;
        }
        return -1;
    }

    void update_lru(int way) {
        lru.erase(std::find(lru.begin(), lru.end(), way));
        lru.push_front(way);
    }

    int get_lru_way() {
        return lru.back();
    }

    void fill(int way, uint64_t tag) {
        lines[way].valid = true;
        lines[way].tag = tag;
        update_lru(way);
    }
};

/* ===================== Q-Learning Agent ===================== */

class QAgent {
public:
    double Q[WAYS][2];
    double alpha = 0.1;
    double gamma = 0.9;
    double epsilon = 0.1;

    QAgent() {
        memset(Q, 0, sizeof(Q));
    }

    int choose_action(int state) {
        if ((double)rand() / RAND_MAX < epsilon)
            return rand() % 2;
        return (Q[state][EVICT] > Q[state][KEEP]) ? EVICT : KEEP;
    }

    void update(int s, int a, double r, int s_next) {
        double best_next = max(Q[s_next][KEEP], Q[s_next][EVICT]);
        Q[s][a] += alpha * (r + gamma * best_next - Q[s][a]);
    }

    void dump() {
        cout << "\nQ-table (state = LRU position)\n";
        for (int i = 0; i < WAYS; i++) {
            cout << "LRU " << i
                 << " | KEEP=" << Q[i][KEEP]
                 << " EVICT=" << Q[i][EVICT] << "\n";
        }
    }
};

/* ===================== Trace Generator ===================== */

vector<uint64_t> generate_trace(int n = 100000) {
    vector<uint64_t> trace;
    trace.reserve(n);

    for (int i = 0; i < n; i++) {
        if ((double)rand() / RAND_MAX < 0.8) {
            trace.push_back((rand() % 16) << 6);   // hot addresses
        } else {
            trace.push_back((rand() % 1024) << 6); // cold
        }
    }
    return trace;
}

/* ===================== Simulation ===================== */

int main() {
    srand(time(nullptr));

    ToyCache cache;
    QAgent agent;
    auto trace = generate_trace();

    int hits = 0, misses = 0;

    for (uint64_t addr : trace) {
        uint64_t tag = addr >> 6;

        int hit_way = cache.find(tag);

        if (hit_way != -1) {
            hits++;
            cache.update_lru(hit_way);

            int s = cache.get_lru_way();
            agent.update(s, KEEP, +1.0, s);
        } else {
            misses++;
            int lru_way = cache.get_lru_way();
            int state = lru_way;

            int action = agent.choose_action(state);

            if (action == EVICT) {
                cache.fill(lru_way, tag);
            }

            int next_state = cache.get_lru_way();
            agent.update(state, action, -1.0, next_state);
        }
    }

    cout << "Hits: " << hits << " Misses: " << misses
         << " Hit Rate: " << (double)hits / (hits + misses) << "\n";

    agent.dump();
    return 0;
}
