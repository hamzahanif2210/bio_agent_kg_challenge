"""Link-prediction eval: GraphSAGE encoder + dot-product decoder.
Same function is run on the Pharos baseline and on the agent-built KG.
Usage: python -m bioagent.eval.baseline PREFIX TARGET_PREDICATE
"""
import sys
import numpy as np
import torch
import torch.nn.functional as F
from sklearn.metrics import roc_auc_score, average_precision_score
from torch_geometric.nn import SAGEConv
from bioagent.schema.kg import read_kg
from bioagent.eval.split import split_edges


class Net(torch.nn.Module):
    def __init__(self, n, d=64):
        super().__init__()
        self.emb = torch.nn.Embedding(n, d)
        self.c1, self.c2 = SAGEConv(d, d), SAGEConv(d, d)

    def forward(self, ei):
        return self.c2(F.relu(self.c1(self.emb.weight, ei)), ei)


def run(prefix, target, epochs=100, seed=0):
    torch.manual_seed(seed)
    nodes, edges = read_kg(prefix)
    ix = {n: i for i, n in enumerate(nodes.id)}
    edges = edges[edges.subject.isin(ix) & edges.object.isin(ix)].reset_index(drop=True)
    te, va, tr = split_edges(edges, target, seed=seed)
    msg = edges.drop(index=np.concatenate([te, va]))
    ei = torch.tensor([msg.subject.map(ix).values, msg.object.map(ix).values])
    ei = torch.cat([ei, ei.flip(0)], 1)
    pos = lambda idx: torch.tensor([edges.loc[idx, "subject"].map(ix).values,
                                    edges.loc[idx, "object"].map(ix).values])
    ptr, pte = pos(tr), pos(te)
    model = Net(len(nodes)); opt = torch.optim.Adam(model.parameters(), 1e-2)
    for _ in range(epochs):
        model.train(); opt.zero_grad()
        z = model(ei)
        neg = torch.randint(0, len(nodes), ptr.shape)
        s = torch.cat([(z[ptr[0]] * z[ptr[1]]).sum(1), (z[neg[0]] * z[neg[1]]).sum(1)])
        y = torch.cat([torch.ones(ptr.size(1)), torch.zeros(ptr.size(1))])
        F.binary_cross_entropy_with_logits(s, y).backward(); opt.step()
    model.eval()
    with torch.no_grad():
        z = model(ei)
        neg = torch.randint(0, len(nodes), pte.shape)
        s = torch.cat([(z[pte[0]] * z[pte[1]]).sum(1), (z[neg[0]] * z[neg[1]]).sum(1)])
        y = np.r_[np.ones(pte.size(1)), np.zeros(pte.size(1))]
    return {"auroc": roc_auc_score(y, s.numpy()), "ap": average_precision_score(y, s.numpy())}


if __name__ == "__main__":
    print(run(sys.argv[1], sys.argv[2]))
