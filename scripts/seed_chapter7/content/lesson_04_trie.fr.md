# 4. Trie (arbre de prefixes)

## 4.1 - Intuition

Comment ranger un dictionnaire pour repondre vite a « combien de mots
commencent par `pre` ? ». Un **trie** (arbre de prefixes) stocke les
mots en partageant leurs prefixes communs : la racine est le mot vide,
chaque arete porte un caractere, et descendre epelle un prefixe.

Deux mots partageant un prefixe partagent le chemin correspondant.
Cette mutualisation rend les requetes par prefixe naturelles - et,
appliquee aux **bits** d'un entier, ouvre les astuces XOR.

---

## 4.2 - Algorithme

```python
class Trie:
    def __init__(self):
        self.child = [{}]     # child[node][c] -> node
        self.cnt = [0]        # nb de mots passant par ce noeud

    def _new(self):
        self.child.append({}); self.cnt.append(0)
        return len(self.child) - 1

    def insert(self, word):
        cur = 0
        for c in word:
            if c not in self.child[cur]:
                self.child[cur][c] = self._new()
            cur = self.child[cur][c]
            self.cnt[cur] += 1

    def count_prefix(self, pref):
        cur = 0
        for c in pref:
            if c not in self.child[cur]:
                return 0
            cur = self.child[cur][c]
        return self.cnt[cur]
```

### Le trie binaire

En stockant un entier par ses bits (du plus significatif au moins),
on obtient un **trie binaire** a deux enfants par noeud. Pour
maximiser $x \oplus y$, on descend en choisissant a chaque bit
l'arete **opposee** au bit de $x$ quand elle existe : chaque bit fixe
ainsi rapporte $2^b$ au resultat.

---

## 4.3 - Complexite

$$
\begin{aligned}
\text{insertion / recherche} &: \Theta(L)\ \text{(longueur du mot)}, \\
\text{comptage par prefixe} &: \Theta(|\text{prefixe}|), \\
\text{XOR maximal (trie binaire)} &: \Theta(B)\ \text{(nb de bits)}.
\end{aligned}
$$

La memoire est $\Theta(\sum L)$ dans le pire cas (aucun prefixe
partage), mais chute des que les mots se ressemblent.

---

## 4.4 - Pieges classiques

1. **Compteur mal place.** Pour le comptage par prefixe, incrementer
   `cnt` sur **chaque** noeud traverse, pas seulement sur la feuille.
2. **Nombre de bits fixe.** Pour le trie binaire, choisir assez de
   bits pour couvrir la valeur maximale (30 bits pour $\le 10^9$).
3. **Explosion memoire.** Un dictionnaire de type `dict` par noeud est
   souple mais lourd ; un tableau de taille fixe (26 lettres, 2 bits)
   est plus rapide si l'alphabet est petit.
4. **Prefixe absent.** Retourner $0$ (ou une valeur sentinelle) des
   qu'une arete manque, sans planter.

---

## 4.5 - Prefixes et bits

Autocompletion, dictionnaires, correction orthographique cotoient les
astuces bit a bit : XOR maximal d'une paire, XOR maximal d'un
sous-tableau (via les XOR prefixes), plus proche voisin en distance de
Hamming. Le trie relie ces deux mondes - textuel et binaire - par une
meme idee : **descendre caractere par caractere**.

---

## 4.6 - Exercices

:::exercise{id="{{EX_DS_TRIE_PREFIX}}"}
:::

:::exercise{id="{{EX_DS_TRIE_XOR}}"}
:::

:::exercise{id="{{EX_DS_MAX_XOR_SUBARRAY}}"}
:::
